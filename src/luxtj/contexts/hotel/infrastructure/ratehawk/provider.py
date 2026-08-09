"""RateHawk hotel provider — mirrors TeenvaHotelRateHawk."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.hotel.domain.common import HotelCommon
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
    HotelBookingDetailsRow,
    HotelBookingPaxDetailsRow,
    HotelBookingTransactionDetailsRow,
)
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.shared_kernel.infrastructure.http import (
    BookingApiRequestResponseRow,
    compress_audit_body,
)
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)

DUMP_DIR_NAME = "ratehawk"
REGIONS_ZST = "regions.zst"
HOTELS_ZST = "hotels.zst"
HOTELS_BY_REGION = "hotels_by_region.json"
REGION_CITIES_CACHE = "region_cities_cache.jsonl"
# Catalog EndPointUrl fallback when admin leaves the field blank (not an env secret).
DEFAULT_RATEHAWK_ENDPOINT = "https://api.worldota.net/api"
CRS_SEARCH_CODE_WINDOW = 400


def _data_dir() -> Path:
    base = Path(os.getenv("LTJBE_DATA_DIR", "data"))
    path = base / DUMP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


class RateHawkHotelProvider(HotelCommon):
    booking_source = "ratehawk"

    RATEHAWK_FINISH_ABORT_ERRORS = {"booking_form_expired", "rate_not_found"}
    RATEHAWK_STATUS_POLL_MAX = 25
    RATEHAWK_STATUS_POLL_INTERVAL_SEC = 5
    RATEHAWK_STATUS_TRANSIENT_ERRORS = {"timeout", "unknown"}
    RATEHAWK_STATUS_TERMINAL_ERRORS = {
        "3ds",
        "block",
        "book_limit",
        "booking_finish_did_not_succeed",
        "charge",
        "decoding_json",
        "endpoint_exceeded_limit",
        "endpoint_not_active",
        "endpoint_not_found",
        "incorrect_credentials",
        "invalid_auth_header",
        "invalid_params",
        "lock",
        "no_auth_header",
        "not_allowed",
        "not_allowed_host",
        "order_not_found",
        "overdue_debt",
        "provider",
        "soldout",
        "unexpected_method",
    }

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        booking_api_id: str | None = None,
        *,
        session: AsyncSession | None = None,
        crs_session: AsyncSession | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        cfg = config or {}
        configs = cfg.get("configs") if isinstance(cfg.get("configs"), dict) else cfg
        self.config = configs if isinstance(configs, dict) else {}
        self.key_id = credential_value(self.config, "API key ID")
        self.api_key = credential_value(self.config, "API key access token")
        endpoint = credential_value(self.config, "EndPointUrl").rstrip("/")
        self.base_url = endpoint or DEFAULT_RATEHAWK_ENDPOINT
        self.api_type = str(cfg.get("api_type") or "") or None
        self.currency = str(cfg.get("currency") or "") or None
        self.booking_api_id = booking_api_id
        self._session = session
        self._crs_session = crs_session or session
        self._http = http_client
        self.cache_ttl_search = 900

    def credentials_ready(self) -> bool:
        return bool(self.key_id and self.api_key)

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{self.key_id}:{self.api_key}".encode()).decode()
        return f"Authorization: Basic {token}"

    def build_post_handle(
        self,
        url: str,
        payload: dict[str, Any],
        headers: list[str] | None = None,
        remarks: str = "",
        timeout: int = 30,
    ) -> dict[str, Any]:
        body = json.dumps(payload)
        default = ["Content-Type: application/json", "Accept: application/json"]
        return {
            "url": url,
            "method": "POST",
            "headers": default + (headers or []),
            "requestBody": body,
            "remarks": remarks,
            "bookingApiId": self.booking_api_id,
            "timeout": timeout,
        }

    async def _send_request(
        self,
        endpoint: str,
        method: str = "POST",
        payload: dict[str, Any] | None = None,
        timeout: float | None = 30,
    ) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + endpoint
        body = json.dumps(payload or {}) if payload else ""
        owns = self._http is None
        client = self._http or httpx.AsyncClient(timeout=timeout or 60.0, verify=False)
        try:
            resp = await client.request(
                method,
                url,
                content=body.encode() if body else None,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                auth=(self.key_id, self.api_key),
                timeout=timeout,
            )
            response_str = resp.text
            http_status = resp.status_code
            errno = 0
        except Exception as exc:
            logger.error("RateHawk HTTP error %s: %s", endpoint, exc)
            response_str = ""
            http_status = 0
            errno = 1
        finally:
            if owns:
                await client.aclose()

        if self._session is not None and self.booking_api_id:
            try:
                now = timeutils.datetime_now()
                stored_req = compress_audit_body(body, request_format="json") if body else None
                stored_res = (
                    compress_audit_body(response_str, request_format="json")
                    if response_str
                    else None
                )
                self._session.add(
                    BookingApiRequestResponseRow(
                        id=str(uuid.uuid4()),
                        booking_api_id=self.booking_api_id,
                        request_type=endpoint,
                        request_format="json",
                        request_url=url,
                        request_headers=json.dumps(
                            ["Authorization: Basic ***", "Content-Type: application/json"]
                        ),
                        request_body=stored_req[:65535] if stored_req else None,
                        response=stored_res[:65535] if stored_res else None,
                        response_status_code=http_status or None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await self._session.flush()
            except Exception as exc:
                logger.warning("RateHawk: failed to log request/response: %s", exc)

        return {"body": response_str, "http_code": http_status, "curl_errno": errno}

    # ── SEARCH ─────────────────────────────────────────────────────────

    async def _resolve_region_id(self, region_id: str) -> str | None:
        """Resolve RateHawk region code from catalogue region id."""
        if not region_id or not self.booking_api_id or self._crs_session is None:
            return None
        from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
            BookingSourceRegionMapRow,
        )

        mapped = (
            await self._crs_session.execute(
                select(BookingSourceRegionMapRow).where(
                    BookingSourceRegionMapRow.booking_source_id == self.booking_api_id,
                    BookingSourceRegionMapRow.new_cities_n_region_id == region_id,
                )
            )
        ).scalar_one_or_none()
        return str(mapped.booking_source_region_code) if mapped is not None else None

    def _build_guests_payload(self, rooms: list[Any]) -> list[dict[str, Any]]:
        if not rooms:
            return [{"adults": 1, "children": []}]
        guests: list[dict[str, Any]] = []
        for room in rooms:
            if not isinstance(room, dict):
                continue
            adults = max(1, min(6, int(room.get("adultCount") or room.get("adult_count") or 1)))
            ages_raw = room.get("childAges") or room.get("child_ages") or []
            child_ages: list[int] = []
            if isinstance(ages_raw, list):
                for a in ages_raw:
                    ai = int(a)
                    if 0 <= ai <= 17:
                        child_ages.append(ai)
            if len(child_ages) > 4:
                child_ages = child_ages[:4]
            guests.append({"adults": adults, "children": child_ages})
        return guests or [{"adults": 1, "children": []}]

    def _build_serp_search_api_cache_key(self, payload: dict[str, Any], *, url: str) -> str:
        """Stable HTTP cache key from SERP payload (not raw body string order quirks).

        Same idea as Mystifly / City Travel: hash logical search params + booking API + URL.
        """
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        material = "|".join(
            [
                encoded,
                str(self.booking_api_id or "0"),
                url,
            ]
        )
        return hashlib.sha256(material.encode()).hexdigest()

    def get_search_request(self, search_data: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.credentials_ready():
            logger.warning(
                "RateHawk credentials missing in booking_apis registry (API key ID / access token)"
            )
            return []
        guests = self._build_guests_payload(search_data.get("rooms") or [])
        # Supplier request currency comes only from booking_apis.currency (admin config).
        request_currency = str(self.currency or AdminCurrency.code() or "USD").upper()[:3]
        checkin = search_data.get("checkin_date") or timeutils.datetime_now().strftime("%Y-%m-%d")
        checkout = search_data.get("checkout_date") or timeutils.datetime_now().strftime("%Y-%m-%d")
        residency = self.ratehawk_residency_from_nationality(search_data)

        lat = search_data.get("lat")
        lng = search_data.get("lng")
        use_geo = lat is not None and lng is not None
        if use_geo:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
            except (TypeError, ValueError):
                return []
            try:
                radius = int(search_data.get("radius") or 25000)
            except (TypeError, ValueError):
                radius = 25000
            radius = max(1, min(70000, radius))
            payload = {
                "checkin": checkin,
                "checkout": checkout,
                "residency": residency,
                "language": "en",
                "guests": guests,
                "latitude": lat_f,
                "longitude": lng_f,
                "radius": radius,
                "currency": request_currency,
            }
            url = self.base_url.rstrip("/") + "/b2b/v3/search/serp/geo/"
        else:
            region_id = search_data.get("_region_id") or search_data.get("region_id")
            if region_id is None:
                return []
            payload = {
                "checkin": checkin,
                "checkout": checkout,
                "residency": residency,
                "language": "en",
                "guests": guests,
                "region_id": int(region_id),
                "currency": request_currency,
            }
            url = self.base_url.rstrip("/") + "/b2b/v3/search/serp/region/"

        handle = self.build_post_handle(
            url,
            payload,
            [self._auth_header()],
            "hotel_search(RateHawk)",
            timeout=60,
        )
        handle["cacheTtl"] = self.cache_ttl_search
        handle["setCache"] = True
        handle["cacheKey"] = self._build_serp_search_api_cache_key(payload, url=url)
        return [handle]

    async def prepare_search_request(self, search_data: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.credentials_ready():
            logger.warning(
                "RateHawk credentials missing in booking_apis registry (API key ID / access token)"
            )
            return []
        lat = search_data.get("lat")
        lng = search_data.get("lng")
        if lat is not None and lng is not None:
            return self.get_search_request(search_data)
        catalogue_region_id = str(search_data.get("region_id") or "")
        region_code = await self._resolve_region_id(catalogue_region_id)
        if region_code is None:
            return []
        search_data["_region_id"] = region_code
        return self.get_search_request(search_data)

    def _parse_serp_hotels(self, raw_response: Any) -> tuple[list[dict[str, Any]], str | None]:
        response = raw_response[0] if isinstance(raw_response, list) else raw_response
        if not response:
            return [], "Empty response from RateHawk"
        try:
            decoded = json.loads(response) if isinstance(response, str) else response
        except Exception:
            return [], "Invalid JSON from RateHawk"
        if not isinstance(decoded, dict) or decoded.get("status") != "ok":
            err = (decoded or {}).get("error") or (decoded or {}).get("debug") or "Unknown error"
            return [], str(err)
        hotels = (decoded.get("data") or {}).get("hotels") or []
        return [h for h in hotels if isinstance(h, dict)], None

    async def iter_search_hotel_batches(
        self, raw_response: Any, search_data: dict[str, Any] | None = None
    ):
        """Yield CRS-windowed hotel cards with prices already converted to admin currency."""
        search_data = search_data or {}
        hotels, err = self._parse_serp_hotels(raw_response)
        if err is not None:
            return

        region_id = search_data.get("_region_id") or search_data.get("region_id") or ""
        booking_api_id = str(search_data.get("booking_api_id") or self.booking_api_id or "")
        booking_source_code = str(search_data.get("booking_source_code") or self.booking_source)
        checkin = str(search_data.get("checkin_date") or "")
        checkout = str(search_data.get("checkout_date") or "")
        nights = self.hotel_stay_nights(checkin, checkout)
        request_currency = str(self.currency or AdminCurrency.code() or "USD").upper()[:3]
        admin_code = AdminCurrency.code()
        guests_payload = self._build_guests_payload(search_data.get("rooms") or [])

        # Preserve SERP order while windowing unique hids for CRS lookups.
        ordered_hids: list[str] = []
        hotels_by_hid: dict[str, dict[str, Any]] = {}
        for api_hotel in hotels:
            hid = str(api_hotel.get("hid") or "")
            if not hid or hid in hotels_by_hid:
                continue
            hotels_by_hid[hid] = api_hotel
            ordered_hids.append(hid)

        for offset in range(0, len(ordered_hids), CRS_SEARCH_CODE_WINDOW):
            window_hids = ordered_hids[offset : offset + CRS_SEARCH_CODE_WINDOW]
            static_by_hid: dict[str, Any] = {}
            if self._crs_session is not None and booking_api_id:
                static_by_hid = await self.get_search_static_details_by_supplier_hotel_codes(
                    self._crs_session, window_hids, booking_api_id
                )

            search_lat = search_data.get("lat")
            search_lng = search_data.get("lng")
            try:
                search_lat_f = float(search_lat) if search_lat is not None else None
                search_lng_f = float(search_lng) if search_lng is not None else None
            except (TypeError, ValueError):
                search_lat_f = search_lng_f = None

            batch: list[dict[str, Any]] = []
            for hid in window_hids:
                api_hotel = hotels_by_hid.get(hid) or {}
                rates = api_hotel.get("rates") or []
                best_rate = self._pick_best_rate(rates)
                if best_rate is None:
                    continue
                pt = self.ratehawk_first_payment_type(best_rate)
                supplier_price = float((pt or {}).get("show_amount") or 0)
                if supplier_price <= 0:
                    continue
                show_currency = str(
                    (pt or {}).get("show_currency_code")
                    or (pt or {}).get("currency_code")
                    or request_currency
                ).upper()[:3] or request_currency
                converted = AdminCurrency.convert_amount_to_admin(supplier_price, show_currency)
                price = float(converted["amount"])
                conversion_rate = float(converted["rate"])

                free_cancel_before = self._extract_free_cancellation_before(best_rate)
                rate_norm = self.ratehawk_normalize_hp_rate_row(best_rate)
                meal_code = str(rate_norm.get("meal_code") or "nomeal")
                meal_included = bool(rate_norm.get("breakfast_included") or meal_code != "nomeal")
                meal_display = str(rate_norm.get("meal_display") or "")
                allotment = int(rate_norm.get("available") or best_rate.get("allotment") or 0)
                tax_breakdown = self.ratehawk_parse_payment_tax_breakdown(pt)
                taxes_included = float(tax_breakdown.get("includedTaxesSum") or 0) > 0 or float(
                    tax_breakdown.get("vatIncludedAmount") or 0
                ) > 0
                serp_filters = [
                    str(f)
                    for f in (best_rate.get("serp_filters") or api_hotel.get("serp_filters") or [])
                    if f
                ]

                static = static_by_hid.get(hid) or {}
                crs = static.get("hotel") or {}
                if not crs or not str(crs.get("name") or "").strip():
                    # Prefer CRS-backed search cards only.
                    continue
                other_amenities = static.get("other_amenities") or []
                amenity_names = [
                    str(a.get("name") or "").strip()
                    for a in other_amenities
                    if isinstance(a, dict) and str(a.get("name") or "").strip()
                ]
                featured_amenity = amenity_names[0] if amenity_names else ""
                name = str(crs.get("name") or "")
                star = int(crs.get("star_rating") or 0)
                unique_key = str(crs.get("unique_key") or "")
                token_region_id = str(crs.get("region_id") or region_id or "")
                if not unique_key and name:
                    unique_key = self.compute_unique_key(name, star, token_region_id or hid)
                if not unique_key:
                    unique_key = __import__("hashlib").md5(f"{hid}|{token_region_id}".encode()).hexdigest()

                rate_key = str(best_rate.get("match_hash") or "")
                if not rate_key:
                    continue

                hotel_lat = float(crs.get("latitude") or 0)
                hotel_lng = float(crs.get("longitude") or 0)
                distance_city_km = None
                if search_lat_f is not None and search_lng_f is not None:
                    distance_city_km = self.haversine_km(
                        search_lat_f, search_lng_f, hotel_lat, hotel_lng
                    )

                meals: list[dict[str, str]] = []
                if meal_included or (meal_code and meal_code.lower() != "nomeal"):
                    icon = "tea" if rate_norm.get("breakfast_included") else "utensils"
                    meals.append(
                        {
                            "icon": icon,
                            "text": meal_display or ("Breakfast included" if meal_included else "Meals included"),
                            "code": meal_code,
                        }
                    )

                token = self.encode_result_token(
                    self.booking_source,
                    json.dumps(
                        {
                            "hid": hid,
                            "region_id": region_id,
                            "region_id": token_region_id,
                            "checkin": checkin,
                            "checkout": checkout,
                            "guests": guests_payload,
                            # Supplier quote currency (book_hash / match_hash is currency-specific).
                            "currency": show_currency,
                            "residency": self.ratehawk_residency_from_nationality(search_data),
                            "rate_key": rate_key,
                            "search_id": search_data.get("search_id") or "",
                        }
                    ),
                )
                address_parts = [
                    p
                    for p in [str(crs.get("address_line1") or ""), str(crs.get("address_line2") or "")]
                    if p
                ]
                property_type = str(crs.get("accommodation_type") or "").strip()
                hotel_chain = str(crs.get("hotel_chain") or "").strip()
                description = str(crs.get("description") or "").strip()
                batch.append(
                    {
                        "HotelCode": hid,
                        "name": name,
                        "star": star,
                        "price": price,
                        "price_per_night": round(price / nights, 2) if nights > 0 else price,
                        "ResultToken": token,
                        "image": str(crs.get("image") or ""),
                        "address": ", ".join(address_parts),
                        "location": str(crs.get("location") or ""),
                        "description": description,
                        "amenities": amenity_names,
                        "other_amenities": other_amenities,
                        "featured_amenity": featured_amenity,
                        "property_type": property_type,
                        "accommodation_type": property_type,
                        "hotel_chain": hotel_chain,
                        "rooms_count": crs.get("rooms_count"),
                        "geoPoint": {
                            "lat": hotel_lat,
                            "lng": hotel_lng,
                        },
                        "distance_city_km": distance_city_km,
                        "distance_city_label": "City Centre",
                        "free_cancellation_before": free_cancel_before or "",
                        "unique_key": unique_key,
                        "booking_source": booking_source_code,
                        "refundable": free_cancel_before is not None,
                        "meal_included": meal_included,
                        "meal_code": meal_code,
                        "meal_display": meal_display,
                        "meals": meals,
                        "serp_filters": serp_filters,
                        "instant_booking": allotment > 0,
                        "book_now": allotment > 0,
                        "taxes_included": taxes_included,
                        "tax_label": "Includes all Taxes" if taxes_included else "Taxes may apply",
                        "show_currency": show_currency,
                        "supplier_currency": show_currency,
                        "currency": admin_code,
                        "conversion_rate": conversion_rate,
                    }
                )
            if batch:
                yield batch

    async def format_search_response(
        self, raw_response: Any, search_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        hotels, err = self._parse_serp_hotels(raw_response)
        if err is not None and not hotels:
            return {"status": False, "data": [], "message": err}
        results: list[dict[str, Any]] = []
        async for batch in self.iter_search_hotel_batches(raw_response, search_data):
            results.extend(batch)
        return {"status": True, "data": results}

    def _pick_best_rate(self, rates: list[Any]) -> dict[str, Any] | None:
        refundable = [
            r
            for r in rates
            if isinstance(r, dict) and self._extract_free_cancellation_before(r) is not None
        ]
        pool = refundable or [r for r in rates if isinstance(r, dict)]
        best = None
        best_price = float("inf")
        for rate in pool:
            pt = self.ratehawk_first_payment_type(rate)
            price = float((pt or {}).get("show_amount") or 0)
            if price < best_price:
                best_price = price
                best = rate
        return best

    def _extract_free_cancellation_before(self, rate: dict[str, Any]) -> str | None:
        pt = self.ratehawk_first_payment_type(rate)
        if pt is None:
            return None
        before = ((pt.get("cancellation_penalties") or {}).get("free_cancellation_before"))
        return str(before) if before else None

    # ── DETAILS / ROOMS / BLOCK ────────────────────────────────────────

    async def get_hotel_details(self, result_token: str) -> dict[str, Any]:
        token_data = self.decode_result_token(result_token)
        if not token_data or self._crs_session is None:
            return {"status": False, "message": "Invalid token"}
        try:
            inner = json.loads(token_data["token"])
        except Exception:
            return {"status": False, "message": "Malformed token"}
        hid = str(inner.get("hid") or "")
        if not hid:
            return {"status": False, "message": "Missing hotel id in token"}
        booking_api_id = str(self.booking_api_id or "")
        crs = await self.get_hotel_crs_details_for_supplier_code(
            self._crs_session, hid, booking_api_id
        )
        if crs is None:
            return {"status": False, "message": "Hotel not found in inventory"}
        resolved_region = str(
            (crs["hotel"].get("region_id") or inner.get("region_id") or "") or ""
        )
        list_inner = {**inner, "region_id": resolved_region}
        if not list_inner.get("guests"):
            list_inner["guests"] = self._build_guests_payload([])
        list_token = self.encode_result_token(
            token_data["booking_source"], json.dumps(list_inner)
        )
        data = await self._build_b2c_hotel_payload_from_crs(crs)
        data["ListToken"] = list_token
        return {"status": True, "data": data}

    async def _build_b2c_hotel_payload_from_crs(self, crs: dict[str, Any]) -> dict[str, Any]:
        hotel = crs["hotel"]
        city_name = str(hotel.get("location") or "")
        country_name = ""
        region_id = str(hotel.get("region_id") or "")
        if self._crs_session is not None and region_id:
            from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
                NewCitiesNRegionRow,
            )

            region = await self._crs_session.get(NewCitiesNRegionRow, region_id)
            if region is not None:
                city_name = str(region.name or city_name)
                country_name = str(region.country_name or "")
        main_image = str(hotel.get("image") or "").strip()
        gallery = crs.get("gallery_image_urls") or []
        images: list[str] = []
        if main_image:
            images.append(main_image)
        for url in gallery:
            u = str(url).strip()
            if u and u not in images:
                images.append(u)
        address_parts = [
            p
            for p in [str(hotel.get("address_line1") or ""), str(hotel.get("address_line2") or "")]
            if p
        ]
        policies_raw = str(hotel.get("hotel_policies") or hotel.get("policy_text") or "")
        amenities_details = [
            {"name": str(am.get("name") or ""), "image": None}
            for am in (crs.get("other_amenities") or [])
        ]
        return {
            "HotelName": str(hotel.get("name") or ""),
            "Description": str(hotel.get("description") or ""),
            "Policies": policies_raw,
            "star": int(hotel.get("star_rating") or 0),
            "location": str(hotel.get("location") or city_name),
            "Images": images,
            "Address": ", ".join(address_parts),
            "RegionId": str(hotel.get("region_id") or ""),
            "CityName": city_name,
            "CountryName": country_name,
            "lat": float(hotel.get("latitude") or 0),
            "lng": float(hotel.get("longitude") or 0),
            "HotelFacilities": [],
            "other_amenities": amenities_details,
            "CheckInTime": str(hotel.get("check_in_time") or "14:00:00"),
            "CheckOutTime": str(hotel.get("check_out_time") or "12:00:00"),
            "classification": str(int(hotel.get("star_rating") or 0)),
        }

    async def get_room_list(self, result_token: str) -> dict[str, Any]:
        token_data = self.decode_result_token(result_token)
        if not token_data:
            return {"status": False, "message": "Invalid token"}
        try:
            inner = json.loads(token_data["token"])
        except Exception:
            return {"status": False, "message": "Malformed token"}
        hid_raw = inner.get("hid") or ""
        payload: dict[str, Any] = {
            "checkin": inner.get("checkin"),
            "checkout": inner.get("checkout"),
            "residency": inner.get("residency") or "gb",
            "language": "en",
            "guests": inner.get("guests") or [],
            "currency": str(inner.get("currency") or "USD").upper(),
        }
        hid_str = str(hid_raw).strip()
        if hid_str.isdigit():
            payload["hid"] = int(hid_str)
        else:
            payload["id"] = hid_str
        meta = await self._send_request("/b2b/v3/search/hp/", "POST", payload, 30)
        if not meta["body"]:
            return {"status": False, "message": "RateHawk API error"}
        decoded = json.loads(meta["body"])
        if not decoded.get("status") or decoded.get("status") != "ok":
            return {"status": False, "message": decoded.get("error") or "Error"}
        rates = (((decoded.get("data") or {}).get("hotels") or [{}])[0].get("rates")) or []
        hid = str(inner.get("hid") or "")
        booking_api_id = str(self.booking_api_id or "")
        hotel_crs_id = ""
        hotel_crs_code = ""
        star = 0
        if hid and booking_api_id and self._crs_session is not None:
            crs_hotel = await self.get_hotel_crs_details_for_supplier_code(
                self._crs_session, hid, booking_api_id
            )
            if crs_hotel:
                hotel_crs_id = str(crs_hotel["hotel"].get("id") or "")
                hotel_crs_code = str(crs_hotel["hotel"].get("code") or "")
                star = int(crs_hotel["hotel"].get("star_rating") or 0)
        room_names = [
            str(r.get("room_name"))
            for r in rates
            if isinstance(r, dict) and r.get("room_name")
        ]
        crs_room_map: dict[str, Any] = {}
        if self._crs_session is not None and hotel_crs_id:
            crs_room_map = await self.get_crs_room_static_by_exact_room_names(
                self._crs_session, hotel_crs_id, room_names
            )
        rooms = self._format_room_list_grouped(rates, result_token, crs_room_map, star)
        return {"status": True, "data": rooms}

    def _format_room_list_grouped(
        self,
        rates: list[Any],
        list_token: str,
        crs_room_by_name: dict[str, Any],
        hotel_star_rating: int,
    ) -> list[dict[str, Any]]:
        token_data = self.decode_result_token(list_token)
        if token_data is None:
            return []
        try:
            base_inner = json.loads(token_data.get("token") or "{}")
        except Exception:
            base_inner = {}
        booking_source_key = str(token_data.get("booking_source") or self.booking_source)
        buckets: dict[str, list[dict[str, Any]]] = {}
        for rate in rates:
            if not isinstance(rate, dict):
                continue
            room_name = str(rate.get("room_name") or "")
            if not room_name:
                continue
            rg = rate.get("rg_ext") if isinstance(rate.get("rg_ext"), dict) else {}
            key = room_name + "\x1e" + json.dumps(rg, sort_keys=True, ensure_ascii=False)
            buckets.setdefault(key, []).append(rate)

        rooms_out: list[dict[str, Any]] = []
        for bucket_rates in buckets.values():
            bucket_rates.sort(
                key=lambda r: float(
                    (self.ratehawk_first_payment_type(r) or {}).get("show_amount") or 0
                )
            )
            first = bucket_rates[0]
            room_name = str(first.get("room_name") or "Room")
            static = crs_room_by_name.get(room_name) or {"images": [], "amenities": []}
            rdt = first.get("room_data_trans") if isinstance(first.get("room_data_trans"), dict) else {}
            desc_parts = [
                p
                for p in [
                    str(rdt.get("main_room_type") or "").strip(),
                    str(rdt.get("bedding_type") or "").strip(),
                ]
                if p
            ]
            description = " ".join(desc_parts).strip() or room_name
            rg_ext = first.get("rg_ext") if isinstance(first.get("rg_ext"), dict) else {}
            max_occ = int(rg_ext["capacity"]) if rg_ext.get("capacity") is not None else None
            variations = [
                self._map_hp_rate_to_room_variation(rate, base_inner, booking_source_key)
                for rate in bucket_rates
            ]
            variations.sort(key=lambda v: float(v.get("amount") or 0))
            totals = [float(v.get("amount") or 0) for v in variations]
            rooms_out.append(
                {
                    "hotelStarRating": hotel_star_rating,
                    "roomName": room_name,
                    "description": description,
                    "images": static.get("images") or [],
                    "amenities": static.get("amenities") or [],
                    "roomVariations": variations,
                    "TotalFare": round(min(totals), 2) if totals else 0.0,
                    "maxOccupancy": max_occ,
                }
            )
        rooms_out.sort(key=lambda r: float(r.get("TotalFare") or 0))
        return rooms_out

    def _map_hp_rate_to_room_variation(
        self, rate: dict[str, Any], base_inner: dict[str, Any], booking_source_key: str
    ) -> dict[str, Any]:
        norm = self.ratehawk_normalize_hp_rate_row(rate)
        pt = self.ratehawk_first_payment_type(rate)
        show_currency = str(
            (pt or {}).get("show_currency_code")
            or (pt or {}).get("currency_code")
            or self.currency
            or AdminCurrency.code()
            or "USD"
        ).upper()[:3]
        converted = AdminCurrency.convert_amount_to_admin(float(norm["amount"] or 0), show_currency)
        taxes_converted = AdminCurrency.convert_amount_to_admin(
            float(norm["taxes"] or 0), show_currency
        )
        admin_code = AdminCurrency.code()
        meal = str(norm["meal_display"] or "Room only")
        free_before = norm.get("free_cancellation_before")
        variation_bits = [meal]
        if free_before:
            variation_bits.append("Free cancellation")
        elif not free_before:
            variation_bits.append("Non-refundable")
        inner = {
            **base_inner,
            "rate_key": norm["book_hash"],
            "currency": show_currency,
        }
        return {
            "variation": " · ".join(variation_bits),
            "amount": float(converted["amount"]),
            "taxes": float(taxes_converted["amount"]),
            "extraFees": norm["extraFees"],
            "meal": meal,
            "meal_code": norm.get("meal_code") or "",
            "breakfastIncluded": norm["breakfast_included"],
            "childMealIncluded": norm["child_meal_included"],
            "available": norm["available"],
            "freeCancellationBefore": free_before,
            "cancelPolicies": norm["cancel_policies"],
            "ResultToken": self.encode_result_token(booking_source_key, json.dumps(inner)),
            "Discount": {"value": 0, "is_percentage": False, "amount": 0},
            "currency": admin_code,
            "supplier_currency": show_currency,
            "conversion_rate": float(converted["rate"]),
        }

    async def block_room(
        self, result_token: str, passengers: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        token_data = self.decode_result_token(result_token)
        if not token_data or self._crs_session is None:
            return {"status": False, "message": "Invalid token"}
        try:
            inner = json.loads(token_data["token"])
        except Exception:
            return {"status": False, "message": "Malformed token"}
        book_hash = str(inner.get("rate_key") or "")
        if not book_hash:
            return {"status": False, "message": "Missing rate key"}
        price_increase = max(0, min(100, int(self.config.get("prebook_price_increase_percent") or 20)))
        meta = await self._send_request(
            "/b2b/v3/hotel/prebook/",
            "POST",
            {"hash": book_hash, "price_increase_percent": price_increase},
            45,
        )
        if not meta["body"]:
            return {"status": False, "message": "RateHawk prebook error"}
        decoded = json.loads(meta["body"])
        if not isinstance(decoded, dict) or decoded.get("status") != "ok":
            err = decoded.get("error") if isinstance(decoded, dict) else "Prebook failed"
            return {"status": False, "message": str(err) if isinstance(err, str) else "Prebook failed"}
        hotels = (decoded.get("data") or {}).get("hotels") or []
        rate = ((hotels[0].get("rates") or [None])[0]) if hotels else None
        if not isinstance(rate, dict):
            return {"status": False, "message": "No rate returned from prebook"}
        new_book_hash = str(rate.get("book_hash") or "")
        if not new_book_hash:
            return {"status": False, "message": "Missing book hash after prebook"}

        hid = str(inner.get("hid") or "")
        booking_api_id = str(self.booking_api_id or "")
        crs = await self.get_hotel_crs_details_for_supplier_code(
            self._crs_session, hid, booking_api_id
        )
        if crs is None:
            return {"status": False, "message": "Hotel not found in inventory"}
        resolved_region = str(
            (crs["hotel"].get("region_id") or inner.get("region_id") or "") or ""
        )
        norm = self.ratehawk_normalize_hp_rate_row(rate)
        pt = self.ratehawk_first_payment_type(rate)
        show_currency = str(
            (pt or {}).get("show_currency_code")
            or (pt or {}).get("currency_code")
            or inner.get("currency")
            or self.currency
            or AdminCurrency.code()
            or "USD"
        ).upper()[:3]
        amount_admin = AdminCurrency.convert_amount_to_admin(float(norm["amount"] or 0), show_currency)
        taxes_admin = AdminCurrency.convert_amount_to_admin(float(norm["taxes"] or 0), show_currency)
        base_admin = AdminCurrency.convert_amount_to_admin(
            float(norm.get("show_amount") or norm["amount"] or 0), show_currency
        )
        room_name_full = norm["room_name"]
        rdt = rate.get("room_data_trans") if isinstance(rate.get("room_data_trans"), dict) else {}
        room_display = str(rdt.get("main_room_type") or "").strip() or room_name_full or "Room"
        hotel_crs_id = str(crs["hotel"].get("id") or "")
        hotel_crs_code = str(crs["hotel"].get("code") or "")
        crs_room_map = (
            await self.get_crs_room_static_by_exact_room_names(
                self._crs_session, hotel_crs_id, [room_name_full]
            )
            if room_name_full
            else {}
        )
        static = crs_room_map.get(room_name_full) or {
            "images": [],
            "amenities": [],
            "supplier_room_code": "",
        }
        hotel_crs_room_code = str(static.get("supplier_room_code") or "")
        amenity_slugs = [
            str(a.get("name") or "")
            for a in (static.get("amenities") or [])
            if a.get("name")
        ]
        api_amenities = [str(a) for a in (rate.get("amenities_data") or [])]
        amenities_combined = list(dict.fromkeys(amenity_slugs + api_amenities))
        guests = inner.get("guests") if isinstance(inner.get("guests"), list) else []
        rooms_payload = self.ratehawk_guests_to_rooms_payload(guests)
        checkin = str(inner.get("checkin") or "")
        checkout = str(inner.get("checkout") or "")
        nights = self.hotel_stay_nights(checkin, checkout)
        list_token_data = {
            "hid": hid,
            "hotel_crs_hotel_code": hotel_crs_code,
            "hotel_crs_room_code": hotel_crs_room_code,
            "book_hash": new_book_hash,
            "checkin": checkin,
            "checkout": checkout,
            "guests": guests,
            "currency": str(inner.get("currency") or "USD"),
            "residency": str(inner.get("residency") or "gb"),
            "search_id": inner.get("search_id") or "",
            "region_id": resolved_region,
        }
        booking_code = self.encode_list_token(
            str(token_data.get("booking_source") or self.booking_source), list_token_data
        )
        hotel_payload = await self._build_b2c_hotel_payload_from_crs(crs)
        room_payload = {
            "Name": room_display,
            "variation": norm["variation_label"],
            "images": static.get("images") or [],
            "amenities": amenities_combined,
            "amount": float(amount_admin["amount"]),
            "taxes": float(taxes_admin["amount"]),
            "extraFees": norm["extraFees"],
            "meal": norm["meal_display"],
            "meal_code": norm["meal_code"],
            "breakfastIncluded": norm["breakfast_included"],
            "childMealIncluded": norm["child_meal_included"],
            "freeCancellationBefore": norm["free_cancellation_before"],
            "cancelPolicies": norm["cancel_policies"],
            "rooms": rooms_payload,
            "paxData": [
                {"Adult": r["adultCount"], "Child": r["childCount"]} for r in rooms_payload
            ],
            "checkInDate": checkin,
            "checkOutDate": checkout,
            "noOfNights": nights,
            "hotelStarRating": int(crs["hotel"].get("star_rating") or 0),
            "BookingCode": booking_code,
            "Discount": {"value": 0, "is_percentage": False, "amount": 0},
            "BaseFare": float(base_admin["amount"]),
            "TotalTax": float(taxes_admin["amount"]),
            "currency": AdminCurrency.code(),
            "supplier_currency": show_currency,
            "conversion_rate": float(amount_admin["rate"]),
        }
        return {
            "status": True,
            "data": {"Hotel": hotel_payload, "room": room_payload, "promocode": []},
        }

    async def pre_book(self, list_token: str) -> dict[str, Any]:
        decoded = self.decode_list_token(list_token)
        if not decoded:
            return {"status": False, "message": "Invalid list token"}
        data = decoded["data"]
        book_hash = data.get("book_hash") or ""
        meta = await self._send_request(
            "/b2b/v3/hotel/order/booking/form/info/",
            "POST",
            {"book_hash": book_hash, "language": "en"},
        )
        if not meta["body"]:
            return {"status": False, "message": "RateHawk API error"}
        result = json.loads(meta["body"])
        if not result.get("status") or result.get("status") != "ok":
            return {"status": False, "message": result.get("error") or "PreBook failed"}
        return {"status": True, "data": result.get("data") or []}

    async def process_booking(self, request: dict[str, Any]) -> dict[str, Any]:
        """Confirm booking with RateHawk (form → finish → poll status)."""
        list_token = request.get("ListToken") or ""
        app_ref = str(request.get("AppReference") or "").strip()
        decoded = self.decode_list_token(list_token)
        if not decoded:
            return {"status": False, "message": "Invalid list token"}
        inner = decoded.get("data") or {}
        book_hash = str(inner.get("book_hash") or "")
        if not book_hash:
            return {"status": False, "message": "Missing book_hash in list token"}
        passengers = request.get("Passengers") if isinstance(request.get("Passengers"), list) else []
        if not passengers:
            return {"status": False, "message": "Passenger details are required"}
        if not app_ref:
            return {"status": False, "message": "AppReference is required for RateHawk booking"}
        if self._session is None:
            return {"status": False, "message": "Session required"}

        lead = (
            await self._session.execute(
                select(HotelBookingPaxDetailsRow)
                .where(HotelBookingPaxDetailsRow.app_reference == app_ref)
                .order_by(HotelBookingPaxDetailsRow.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if lead is None:
            return {"status": False, "message": "Lead guest not found for booking"}

        partner_order_id = str(uuid.uuid4())
        user_ip = str(request.get("user_ip") or "127.0.0.1")
        form_meta = await self._send_request(
            "/b2b/v3/hotel/order/booking/form/",
            "POST",
            {
                "partner_order_id": partner_order_id,
                "book_hash": book_hash,
                "language": "en",
                "user_ip": user_ip,
            },
            None,
        )
        if not form_meta["body"] or form_meta["curl_errno"]:
            return {"status": False, "message": "RateHawk API error (booking form)"}
        form_result = json.loads(form_meta["body"])
        if not isinstance(form_result, dict) or form_result.get("status") != "ok":
            return {
                "status": False,
                "message": self._format_error(
                    "booking form", form_result if isinstance(form_result, dict) else None
                ),
            }
        form_data = form_result.get("data") if isinstance(form_result.get("data"), dict) else {}
        order_id = form_data.get("order_id")
        payment_types = (
            form_data.get("payment_types")
            if isinstance(form_data.get("payment_types"), list)
            else []
        )
        chosen = next(
            (pt for pt in payment_types if isinstance(pt, dict) and pt.get("type") == "deposit"),
            None,
        ) or next((pt for pt in payment_types if isinstance(pt, dict)), None)
        if chosen is None:
            return {"status": False, "message": "RateHawk did not return any payment_types for this rate"}
        payment_type_finish = {
            "type": str(chosen.get("type") or ""),
            "amount": str(chosen.get("amount") or ""),
            "currency_code": str(chosen.get("currency_code") or "").upper()[:3],
        }
        if (
            not payment_type_finish["type"]
            or not payment_type_finish["amount"]
            or len(payment_type_finish["currency_code"]) != 3
        ):
            return {"status": False, "message": "Invalid payment_type from RateHawk (currency_code)"}

        rooms = self._build_finish_rooms(
            passengers, inner.get("guests") if isinstance(inner.get("guests"), list) else []
        )
        if not rooms:
            return {"status": False, "message": "Could not build rooms/guests for RateHawk finish"}

        guest_email = str(lead.email or "").strip()
        if not guest_email:
            return {"status": False, "message": "Lead guest email is required for RateHawk booking"}

        txn = (
            await self._session.execute(
                select(HotelBookingTransactionDetailsRow).where(
                    HotelBookingTransactionDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        amount_sell = (
            f"{float(txn.total):.2f}"
            if txn is not None
            and str(txn.currency).upper()[:3] == payment_type_finish["currency_code"]
            else str(chosen.get("amount") or "0.00")
        )

        finish_payload = {
            "user": {"email": guest_email, "phone": re_digits(str(lead.phone_code or ""), str(lead.phone or "")) or "00000"},
            "supplier_data": {
                k: v
                for k, v in {
                    "first_name_original": str(lead.first_name or "").strip(),
                    "last_name_original": str(lead.last_name or "").strip(),
                    "phone": re_digits(str(lead.phone_code or ""), str(lead.phone or "")) or None,
                    "email": guest_email,
                }.items()
                if v
            },
            "partner": {
                "partner_order_id": partner_order_id,
                "comment": f"LuxTJ {app_ref}",
                "amount_sell_b2b2c": amount_sell,
            },
            "language": "en",
            "rooms": rooms,
            "payment_type": payment_type_finish,
        }
        finish_meta = await self._send_request(
            "/b2b/v3/hotel/order/booking/finish/", "POST", finish_payload, None
        )
        finish_result = json.loads(finish_meta["body"]) if finish_meta["body"] else None
        if isinstance(finish_result, dict):
            finish_err = str(finish_result.get("error") or "").lower()
            if finish_err in self.RATEHAWK_FINISH_ABORT_ERRORS:
                return {
                    "status": False,
                    "message": self._format_error("booking finish", finish_result),
                }

        await self._persist_partner_ids(app_ref, partner_order_id, order_id)
        poll = await self._poll_booking_finish_status(partner_order_id)
        if not poll.get("ok"):
            if poll.get("message") == "booking_timeout":
                return {
                    "status": True,
                    "pending_supplier_confirmation": True,
                    "data": {
                        "BookingRef": str(order_id or partner_order_id),
                        "ConfirmationReference": "",
                        "Status": "BOOKING_AWAITING_CONFIRMATION",
                        "HotelCode": str(inner.get("hid") or ""),
                        "RawResponse": {"form": form_data, "finish_pending": True},
                    },
                }
            return {"status": False, "message": poll.get("message") or "booking_timeout"}

        return {
            "status": True,
            "data": {
                "BookingRef": str(order_id or partner_order_id),
                "ConfirmationReference": "",
                "Status": "BOOKING_PENDING",
                "HotelCode": str(inner.get("hid") or ""),
                "RawResponse": {"form": form_data, "finish_status": poll.get("data")},
            },
        }

    async def _persist_partner_ids(
        self, app_ref: str, partner_order_id: str, order_id: Any
    ) -> None:
        if self._session is None:
            return
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if not booking:
            return
        attrs = dict(booking.attributes or {})
        attrs["ratehawk_partner_order_id"] = partner_order_id
        if order_id is not None and order_id != "":
            attrs["ratehawk_order_id"] = order_id
        attrs["ratehawk_finish_pending"] = True
        booking.attributes = attrs
        await self._session.flush()

    async def _poll_booking_finish_status(self, partner_order_id: str) -> dict[str, Any]:
        import asyncio

        for i in range(self.RATEHAWK_STATUS_POLL_MAX):
            if i > 0:
                await asyncio.sleep(self.RATEHAWK_STATUS_POLL_INTERVAL_SEC)
            round_result = await self._poll_finish_status_one_round(partner_order_id)
            if round_result["decision"] == "success":
                return {"ok": True, "data": round_result["data"]}
            if round_result["decision"] == "terminal_failure":
                return {"ok": False, "message": round_result["message"]}
        return {"ok": False, "message": "booking_timeout"}

    async def _poll_finish_status_one_round(self, partner_order_id: str) -> dict[str, Any]:
        meta = await self._send_request(
            "/b2b/v3/hotel/order/booking/finish/status/",
            "POST",
            {"partner_order_id": partner_order_id},
            None,
        )
        if meta["curl_errno"] or meta["http_code"] >= 500 or not meta["body"]:
            return {"decision": "continue"}
        try:
            res = json.loads(meta["body"])
        except Exception:
            return {"decision": "continue"}
        if not isinstance(res, dict):
            return {"decision": "continue"}
        st = res.get("status") or ""
        err = res.get("error")
        err_str = str(err).lower() if isinstance(err, str) else ""
        if st == "ok" and not err:
            return {
                "decision": "success",
                "data": res.get("data") if isinstance(res.get("data"), dict) else {},
            }
        if err_str in self.RATEHAWK_STATUS_TRANSIENT_ERRORS:
            return {"decision": "continue"}
        if err_str in self.RATEHAWK_STATUS_TERMINAL_ERRORS:
            return {
                "decision": "terminal_failure",
                "message": self._format_error("booking finish status", res),
            }
        return {"decision": "continue"}

    def _build_finish_rooms(
        self, passengers: list[Any], list_guests: list[Any]
    ) -> list[dict[str, Any]]:
        queue = []
        for pax in passengers:
            if not isinstance(pax, dict):
                continue
            queue.append(
                {
                    "first_name": str(pax.get("FirstName") or pax.get("first_name") or "").strip(),
                    "last_name": str(pax.get("LastName") or pax.get("last_name") or "").strip(),
                }
            )
        if not queue:
            return []
        all_slots = list(queue)
        specs = self.ratehawk_guests_to_rooms_payload(list_guests)
        rooms_out: list[dict[str, Any]] = []
        for spec in specs:
            adults = max(0, int(spec.get("adultCount") or 0))
            child_ages = [int(a) for a in (spec.get("childAges") or [])]
            guests: list[dict[str, Any]] = []
            for _ in range(adults):
                p = queue.pop(0) if queue else None
                if p and (p["first_name"] or p["last_name"]):
                    guests.append(
                        {
                            "first_name": p["first_name"] or "Guest",
                            "last_name": p["last_name"] or "Adult",
                        }
                    )
                else:
                    guests.append({"first_name": "Guest", "last_name": "Adult"})
            for age in child_ages:
                p = queue.pop(0) if queue else None
                if p and (p["first_name"] or p["last_name"]):
                    guests.append(
                        {
                            "first_name": p["first_name"] or "Child",
                            "last_name": p["last_name"] or "Guest",
                            "is_child": True,
                            "age": max(0, int(age)),
                        }
                    )
                else:
                    guests.append(
                        {
                            "first_name": "Child",
                            "last_name": "Guest",
                            "is_child": True,
                            "age": max(0, int(age)),
                        }
                    )
            if guests:
                rooms_out.append({"guests": guests})
        if not rooms_out:
            return [
                {
                    "guests": [
                        {
                            "first_name": g["first_name"] or "Guest",
                            "last_name": g["last_name"] or "Guest",
                        }
                        for g in all_slots
                    ]
                }
            ]
        return rooms_out

    def _format_error(self, step: str, result: dict[str, Any] | None) -> str:
        msg = str((result or {}).get("error") or "unknown") if result else "invalid response"
        debug = (result or {}).get("debug") if result else None
        if isinstance(debug, dict) and debug.get("validation_error"):
            msg += " — " + str(debug["validation_error"])
        return f"RateHawk {step} failed: {msg}"

    @staticmethod
    def _confirmation_ref_from_order_row(order: dict[str, Any]) -> str:
        sd = order.get("supplier_data")
        if isinstance(sd, dict):
            cid = str(sd.get("confirmation_id") or "").strip()
            if cid:
                return cid
            so = str(sd.get("order_id") or "").strip()
            if so:
                return so
        oid = order.get("order_id")
        if oid is not None and oid != "":
            return str(oid)
        return ""

    @staticmethod
    def _map_order_status(order_status: str) -> str | None:
        st = str(order_status or "").strip().lower()
        if not st:
            return None
        if st in {"cancelled", "canceled", "cancelled_by_partner", "cancelled_by_hotel"}:
            return "CANCELLED"
        if st in {"ok", "completed", "confirmed"}:
            return "BOOKING_CONFIRMED"
        if st in {"rejected", "failed", "error"}:
            return "BOOKING_FAILED"
        return None

    async def _fetch_order_info(
        self, partner_order_id: str, order_id: Any
    ) -> dict[str, Any]:
        """POST hotel/order/info/ — confirmation ref + order row status."""
        out: dict[str, Any] = {
            "confirmation_reference": "",
            "order_status": None,
            "order_row": None,
            "order_info_raw": None,
            "order_id": order_id,
        }
        searches: list[dict[str, Any]] = []
        if partner_order_id:
            searches.append({"partner_order_ids": [partner_order_id]})
            searches.append({"partner_order_ids": [partner_order_id], "status": "ok"})
        if order_id is not None and order_id != "":
            try:
                oid = int(order_id)
            except (TypeError, ValueError):
                oid = None
            if oid is not None and oid > 0:
                searches.append({"order_ids": [oid]})
                searches.append({"order_ids": [oid], "status": "ok"})

        for search in searches:
            payload = {
                "language": "en",
                "ordering": {"ordering_type": "desc", "ordering_by": "created_at"},
                "pagination": {"page_size": "10", "page_number": "1"},
                "search": search,
            }
            meta = await self._send_request(
                "/b2b/v3/hotel/order/info/", "POST", payload, None
            )
            if meta.get("curl_errno") or not meta.get("body"):
                continue
            try:
                decoded = json.loads(meta["body"])
            except Exception:
                continue
            if not isinstance(decoded, dict) or decoded.get("status") != "ok":
                continue
            data = decoded.get("data") if isinstance(decoded.get("data"), dict) else {}
            orders = data.get("orders") if isinstance(data, dict) else None
            if not isinstance(orders, list) or not orders:
                continue
            first = orders[0]
            if not isinstance(first, dict):
                continue
            ref = self._confirmation_ref_from_order_row(first)
            out["confirmation_reference"] = ref
            out["order_status"] = first.get("status")
            out["order_row"] = first
            out["order_info_raw"] = data
            if first.get("order_id") is not None:
                out["order_id"] = first.get("order_id")
            if ref or out["order_status"]:
                break
        return out

    async def refresh_booking_from_supplier(
        self, booking_reference: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Poll finish/status (when awaiting) and/or order/info for confirmation."""
        import asyncio

        ctx = context if isinstance(context, dict) else {}
        partner_order_id = str(
            ctx.get("partner_order_id") or booking_reference or ""
        ).strip()
        order_id = ctx.get("order_id")
        if order_id is None or order_id == "":
            order_id = booking_reference if str(booking_reference).strip().isdigit() else None
        current_status = str(ctx.get("current_status") or "").upper()

        if not partner_order_id and (order_id is None or order_id == ""):
            return {
                "status": False,
                "message": "Supplier booking reference is missing",
                "outcome": "missing_ref",
                "data": {},
            }

        finish_status_data: dict[str, Any] | None = None
        if current_status in {
            "BOOKING_AWAITING_CONFIRMATION",
            "BOOKING_PENDING",
            "PENDING_PAYMENT",
        } or bool(ctx.get("finish_pending")):
            if partner_order_id:
                round_result = await self._poll_finish_status_one_round(partner_order_id)
                if round_result["decision"] == "terminal_failure":
                    return {
                        "status": True,
                        "message": round_result.get("message") or "Supplier booking failed",
                        "outcome": "failed",
                        "data": {
                            "BookingRef": str(order_id or partner_order_id),
                            "ConfirmationReference": "",
                            "Status": "BOOKING_FAILED",
                            "RawResponse": {
                                "finish_status_error": round_result.get("message"),
                            },
                        },
                    }
                if round_result["decision"] == "success":
                    finish_status_data = (
                        round_result["data"]
                        if isinstance(round_result.get("data"), dict)
                        else {}
                    )
                    await asyncio.sleep(self.RATEHAWK_STATUS_POLL_INTERVAL_SEC)

        order_info = await self._fetch_order_info(partner_order_id, order_id)
        mapped = self._map_order_status(str(order_info.get("order_status") or ""))
        conf = str(order_info.get("confirmation_reference") or "").strip()
        booking_ref = str(
            order_info.get("order_id") or order_id or partner_order_id or ""
        )

        raw: dict[str, Any] = {
            "order_info": order_info.get("order_info_raw"),
            "order_row": order_info.get("order_row"),
        }
        if finish_status_data is not None:
            raw["finish_status"] = finish_status_data

        if mapped == "CANCELLED":
            return {
                "status": True,
                "message": "Booking cancelled at supplier",
                "outcome": "cancelled",
                "data": {
                    "BookingRef": booking_ref,
                    "ConfirmationReference": conf,
                    "Status": "CANCELLED",
                    "RawResponse": raw,
                },
            }
        if mapped == "BOOKING_FAILED":
            return {
                "status": True,
                "message": "Booking failed at supplier",
                "outcome": "failed",
                "data": {
                    "BookingRef": booking_ref,
                    "ConfirmationReference": conf,
                    "Status": "BOOKING_FAILED",
                    "RawResponse": raw,
                },
            }
        if finish_status_data is not None or mapped == "BOOKING_CONFIRMED" or conf:
            return {
                "status": True,
                "message": "Status updated",
                "outcome": "confirmed",
                "data": {
                    "BookingRef": booking_ref,
                    "ConfirmationReference": conf,
                    "Status": "BOOKING_CONFIRMED",
                    "RawResponse": raw,
                },
            }

        # Do not downgrade an already-confirmed (or other terminal) local status
        # when supplier order/info is temporarily empty.
        if current_status == "BOOKING_CONFIRMED":
            return {
                "status": True,
                "message": "No supplier updates",
                "outcome": "unchanged",
                "data": {
                    "BookingRef": booking_ref,
                    "ConfirmationReference": conf,
                    "Status": "BOOKING_CONFIRMED",
                    "RawResponse": raw,
                },
            }
        if current_status == "BOOKING_FAILED":
            return {
                "status": True,
                "message": "No supplier updates",
                "outcome": "unchanged",
                "data": {
                    "BookingRef": booking_ref,
                    "ConfirmationReference": conf,
                    "Status": "BOOKING_FAILED",
                    "RawResponse": raw,
                },
            }

        return {
            "status": True,
            "message": "Still awaiting supplier confirmation",
            "outcome": "awaiting",
            "data": {
                "BookingRef": booking_ref,
                "ConfirmationReference": conf,
                "Status": "BOOKING_AWAITING_CONFIRMATION",
                "RawResponse": raw,
            },
        }

    async def get_booking_details(self, booking_reference: str) -> dict[str, Any]:
        meta = await self._send_request(
            "/b2b/v3/hotel/order/details/",
            "POST",
            {"id": booking_reference, "language": "en"},
        )
        if not meta["body"]:
            return {"status": False, "message": "RateHawk API error"}
        result = json.loads(meta["body"])
        if not result.get("status") or result.get("status") != "ok":
            return {"status": False, "message": result.get("error") or "Error"}
        return {"status": True, "data": result.get("data") or []}

    async def cancel_booking(self, booking_reference: str) -> dict[str, Any]:
        meta = await self._send_request(
            "/b2b/v3/hotel/order/booking/cancel/",
            "POST",
            {"id": booking_reference},
        )
        if not meta["body"]:
            return {"status": False, "message": "RateHawk API error"}
        result = json.loads(meta["body"])
        if not result.get("status") or result.get("status") != "ok":
            return {"status": False, "message": result.get("error") or "Cancel failed"}
        return {"status": True, "data": result.get("data") or []}

    # ── STATIC DUMPS (CRS mapping) ─────────────────────────────────────

    async def get_region_dump_url(self) -> str | None:
        meta = await self._send_request("/b2b/v3/hotel/region/dump/", "GET", {}, 60)
        if not meta["body"]:
            return None
        data = json.loads(meta["body"])
        if not data.get("status") or data.get("status") != "ok":
            return None
        return (data.get("data") or {}).get("url")

    async def fetch_and_cache_region_cities(self) -> dict[str, Any]:
        url = await self.get_region_dump_url()
        if not url:
            return {"total_cities": 0, "error": "Failed to get region dump URL from API"}
        zst_path = _data_dir() / REGIONS_ZST
        json_path = zst_path.with_suffix(".json")
        cache_path = _data_dir() / REGION_CITIES_CACHE
        for p in (zst_path, json_path, cache_path):
            p.unlink(missing_ok=True)
        if not await self._download_file(url, zst_path):
            return {"total_cities": 0, "error": "Failed to download region dump"}
        extracted = self._extract_zst(zst_path)
        if extracted is None:
            return {
                "total_cities": 0,
                "error": "Failed to extract .zst (install zstd CLI)",
            }
        count = self._write_region_cities_cache(extracted, cache_path)
        extracted.unlink(missing_ok=True)
        if count < 0:
            return {"total_cities": 0, "error": "Failed to write region cities cache"}
        return {"total_cities": count, "error": ""}

    def get_region_cities_cache_path(self) -> Path:
        return _data_dir() / REGION_CITIES_CACHE

    def _write_region_cities_cache(self, dump_path: Path, cache_path: Path) -> int:
        count = 0
        try:
            with dump_path.open("r", encoding="utf-8", errors="replace") as inp, cache_path.open(
                "w", encoding="utf-8"
            ) as out:
                for line in inp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(obj, dict) or obj.get("type") != "City":
                        continue
                    name_obj = obj.get("name") if isinstance(obj.get("name"), dict) else {}
                    country_obj = (
                        obj.get("country_name")
                        if isinstance(obj.get("country_name"), dict)
                        else {}
                    )
                    row = {
                        "id": int(obj.get("id") or 0),
                        "name": str(name_obj.get("en") or ""),
                        "country_name": str(country_obj.get("en") or ""),
                        "country_code": str(obj.get("country_code") or ""),
                    }
                    if row["id"] == 0 or not row["name"]:
                        continue
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
        except Exception:
            return -1
        return count

    async def get_hotel_dump_url(self) -> str | None:
        meta = await self._send_request(
            "/b2b/v3/hotel/info/dump/",
            "POST",
            {"inventory": "all", "language": "en"},
            120,
        )
        if not meta["body"]:
            return None
        data = json.loads(meta["body"])
        if not data.get("status") or data.get("status") != "ok":
            return None
        return (data.get("data") or {}).get("url")

    async def download_hotel_dump_file(self) -> dict[str, Any]:
        url = await self.get_hotel_dump_url()
        if not url:
            return {"success": False, "error": "Failed to get hotel dump URL from API", "bytes": 0}
        zst_path = _data_dir() / HOTELS_ZST
        idx_path = _data_dir() / HOTELS_BY_REGION
        zst_path.unlink(missing_ok=True)
        zst_path.with_suffix(".json").unlink(missing_ok=True)
        idx_path.unlink(missing_ok=True)
        if not await self._download_file(url, zst_path):
            return {"success": False, "error": "Failed to download hotel dump", "bytes": 0}
        return {"success": True, "error": "", "bytes": zst_path.stat().st_size}

    async def extract_hotel_dump_and_build_index(self) -> dict[str, Any]:
        zst_path = _data_dir() / HOTELS_ZST
        save_path = _data_dir() / HOTELS_BY_REGION
        if not zst_path.is_file() or zst_path.stat().st_size == 0:
            return {
                "success": False,
                "error": "No hotels.zst file. Download the dump first (step 1).",
                "regions_count": 0,
            }
        zst_path.with_suffix(".json").unlink(missing_ok=True)
        save_path.unlink(missing_ok=True)
        extracted = self._extract_zst(zst_path)
        if extracted is None:
            return {
                "success": False,
                "error": "Failed to extract .zst (install zstd CLI)",
                "regions_count": 0,
            }
        by_region = self.parse_hotels_from_dump(extracted)
        extracted.unlink(missing_ok=True)
        save_path.write_text(json.dumps(by_region, ensure_ascii=False), encoding="utf-8")
        return {"success": True, "error": "", "regions_count": len(by_region)}

    def get_hotel_dump_state(self) -> dict[str, Any]:
        zst_path = _data_dir() / HOTELS_ZST
        idx_path = _data_dir() / HOTELS_BY_REGION
        has_zst = zst_path.is_file() and zst_path.stat().st_size > 0
        has_idx = idx_path.is_file() and idx_path.stat().st_size > 0
        regions = 0
        if has_idx:
            try:
                regions = len(json.loads(idx_path.read_text(encoding="utf-8")))
            except Exception:
                regions = 0
        return {
            "has_zst": has_zst,
            "zst_bytes": zst_path.stat().st_size if has_zst else 0,
            "has_index": has_idx,
            "regions_count": regions,
        }

    def get_hotels_by_region_file_path(self) -> Path:
        return _data_dir() / HOTELS_BY_REGION

    def get_hotels_by_region(self, region_id: str) -> list[dict[str, Any]]:
        path = self.get_hotels_by_region_file_path()
        if not path.is_file():
            return []
        try:
            by_region = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return by_region.get(region_id) or [] if isinstance(by_region, dict) else []

    @staticmethod
    def normalize_dump_hotel_payload(row: dict[str, Any]) -> dict[str, Any]:
        if isinstance(row.get("data"), dict):
            inner = row["data"]
            if any(
                k in inner
                for k in (
                    "hid",
                    "name",
                    "hotel_chain",
                    "amenity_groups",
                    "room_groups",
                    "images",
                )
            ):
                return inner
        return row

    def parse_hotels_from_dump(self, path: Path) -> dict[str, list[dict[str, Any]]]:
        by_region: dict[str, list[dict[str, Any]]] = {}
        if not path.is_file():
            return by_region
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                hotel = self.normalize_dump_hotel_payload(obj)
                if obj.get("deleted") or obj.get("is_closed") or hotel.get("deleted") or hotel.get(
                    "is_closed"
                ):
                    continue
                region = hotel.get("region") if isinstance(hotel.get("region"), dict) else None
                if not region or "id" not in region:
                    continue
                by_region.setdefault(str(region["id"]), []).append(hotel)
        return by_region

    def format_dump_hotel_for_blender(self, hotel: dict[str, Any]) -> dict[str, Any]:
        hotel = self.normalize_dump_hotel_payload(hotel)
        hotel_id = str(hotel.get("hid") or "NAN")
        name = str(hotel.get("name") or "")
        star = int(hotel.get("star_rating") or 0)
        address = str(hotel.get("address") or "")
        region = hotel.get("region") if isinstance(hotel.get("region"), dict) else {}
        location = str(region.get("name") or "")
        description = ""
        if isinstance(hotel.get("description_struct"), list):
            parts: list[str] = []
            for block in hotel["description_struct"]:
                if isinstance(block, dict) and isinstance(block.get("paragraphs"), list):
                    parts.extend(str(p) for p in block["paragraphs"])
            description = " ".join(parts)
        images: list[dict[str, str]] = []
        image = ""
        for url in hotel.get("images") or []:
            url = str(url).replace("{size}", "1080x")
            if not image:
                image = url
            images.append({"url": url, "caption": "", "category_slug": ""})
        if not image and isinstance(hotel.get("images_ext"), list) and hotel["images_ext"]:
            first = hotel["images_ext"][0]
            if isinstance(first, dict) and first.get("url"):
                image = str(first["url"]).replace("{size}", "1080x")
                images.append(
                    {
                        "url": image,
                        "caption": "",
                        "category_slug": str(first.get("category_slug") or ""),
                    }
                )
        geo_point: dict[str, float] = {}
        if "latitude" in hotel and "longitude" in hotel:
            geo_point = {"lat": float(hotel["latitude"]), "lng": float(hotel["longitude"])}
        amenities: list[Any] = []
        for group in hotel.get("amenity_groups") or []:
            if isinstance(group, dict) and isinstance(group.get("amenities"), list):
                amenities.extend(group["amenities"])
        return {
            "HotelCode": hotel_id,
            "name": name,
            "star": star,
            "address": address,
            "geoPoint": geo_point,
            "location": location,
            "hotelPhone": str(hotel.get("phone") or ""),
            "email": str(hotel.get("email") or ""),
            "zipCode": str(hotel.get("postal_code") or ""),
            "allamenities": amenities,
            "amenity_groups": hotel.get("amenity_groups")
            if isinstance(hotel.get("amenity_groups"), list)
            else [],
            "room_groups": hotel.get("room_groups")
            if isinstance(hotel.get("room_groups"), list)
            else [],
            "image": image,
            "images": images,
            "free_cancellation": False,
            "price": 0,
            "ResultToken": "NAN",
            "_booking_source": self.booking_source,
            "description": description,
            "policy_struct": hotel.get("policy_struct")
            if isinstance(hotel.get("policy_struct"), list)
            else [],
            "metapolicy_struct": hotel.get("metapolicy_struct")
            if isinstance(hotel.get("metapolicy_struct"), dict)
            else {},
            "metapolicy_extra_info": str(hotel.get("metapolicy_extra_info") or ""),
            "facts": hotel.get("facts") if isinstance(hotel.get("facts"), dict) else {},
            "payment_methods": hotel.get("payment_methods")
            if isinstance(hotel.get("payment_methods"), list)
            else [],
            "serp_filters": hotel.get("serp_filters")
            if isinstance(hotel.get("serp_filters"), list)
            else [],
            "front_desk_time_start": str(hotel.get("front_desk_time_start") or ""),
            "front_desk_time_end": str(hotel.get("front_desk_time_end") or ""),
            "checkIn": str(hotel.get("check_in_time") or "14:00:00"),
            "checkOut": str(hotel.get("check_out_time") or "12:00:00"),
        }

    async def _download_file(self, url: str, save_path: Path) -> bool:
        owns = self._http is None
        client = self._http or httpx.AsyncClient(timeout=300.0, verify=False, follow_redirects=True)
        try:
            headers = {
                "Accept": "*/*",
                "User-Agent": "LuxTJ/1.0 (RateHawk dump downloader)",
            }
            auth = None
            from urllib.parse import urlparse

            if urlparse(url).hostname == urlparse(self.base_url).hostname:
                auth = (self.key_id, self.api_key)
            async with client.stream("GET", url, headers=headers, auth=auth) as resp:
                if resp.status_code >= 400:
                    return False
                with save_path.open("wb") as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)
            if not save_path.is_file() or save_path.stat().st_size == 0:
                return False
            head = save_path.read_bytes()[:4]
            if head != b"\x28\xb5\x2f\xfd":
                save_path.unlink(missing_ok=True)
                return False
            return True
        except Exception as exc:
            logger.warning("RateHawk dump download failed: %s", exc)
            save_path.unlink(missing_ok=True)
            return False
        finally:
            if owns:
                await client.aclose()

    def _extract_zst(self, zst_path: Path) -> Path | None:
        json_path = zst_path.with_suffix(".json")
        json_path.unlink(missing_ok=True)
        zstd_bin = shutil.which("zstd") or os.getenv("ZSTD_PATH")
        if not zstd_bin or not Path(zstd_bin).exists():
            for candidate in ("/usr/bin/zstd", "/usr/local/bin/zstd", "/opt/homebrew/bin/zstd"):
                if Path(candidate).exists():
                    zstd_bin = candidate
                    break
        if not zstd_bin:
            logger.error("RateHawk: zstd CLI not found")
            return None
        try:
            subprocess.run(
                [zstd_bin, "-d", str(zst_path), "-o", str(json_path), "-f"],
                check=True,
                capture_output=True,
            )
        except Exception as exc:
            logger.error("RateHawk: zstd extraction failed: %s", exc)
            return None
        return json_path if json_path.is_file() else None


def re_digits(code: str, phone: str) -> str:
    import re

    return re.sub(r"\D+", "", code + phone)
