"""City Travel flight provider — Search through PreBook (pay-then-hold draft)."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
from typing import Any

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.country import get_country_service
from luxtj.contexts.flight.infrastructure.citytravel import normalize as ct_norm
from luxtj.contexts.flight.infrastructure.citytravel.soap import CityTravelSoap
from luxtj.contexts.flight.infrastructure.token_cache import cache_get, cache_put
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.shared_kernel.infrastructure.http import HandleDescriptor, MultiHttpClient
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED = "not implemented yet"
CACHE_TTL_TOKEN = 45 * 60
CACHE_TTL_HTTP_SEARCH = 900  # 15 min — same idea as Mystifly CACHE_TTL_SEARCH_API


class CityTravelFlightProvider:
    """City Travel (`citytravel`) booking source."""

    booking_source = "citytravel"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        booking_api_id: str | None = None,
        *,
        session: Any | None = None,
        http_client: Any | None = None,
        multi_http: MultiHttpClient | None = None,
    ) -> None:
        cfg = config or {}
        configs = cfg.get("configs") if isinstance(cfg.get("configs"), dict) else cfg
        self.config = configs if isinstance(configs, dict) else {}
        self.booking_api_id = booking_api_id
        self._session = session
        self._http = http_client
        self._curl = multi_http or MultiHttpClient(http_client, session=session)

        self.api_login = credential_value(self.config, "ApiLogin")
        self.api_password = credential_value(self.config, "ApiPassword")
        self.token_guid = (
            credential_value(self.config, "TokenGuid")
            or "00000000-0000-0000-0000-000000000000"
        )
        self.device_id = credential_value(self.config, "DeviceId") or "test"
        self.endpoint_url = credential_value(self.config, "EndPointUrl").rstrip("/")
        self.currency = str(cfg.get("currency") or "").strip().upper() or None
        self.api_type = str(cfg.get("api_type") or "") or None

    def credentials_ready(self) -> bool:
        return bool(self.api_login and self.api_password and self.endpoint_url)

    def supplier_currency(self) -> str:
        return (self.currency or AdminCurrency.code() or "USD").upper()[:3]

    @staticmethod
    def _todo(method: str, note: str = "") -> dict[str, Any]:
        msg = f"CityTravel.{method} {_NOT_IMPLEMENTED}"
        if note:
            msg = f"{msg} — {note}"
        return {"status": False, "data": [], "message": msg}

    def _auth_info(self) -> dict[str, Any]:
        return CityTravelSoap.auth_info(
            api_login=self.api_login,
            api_password=self.api_password,
            currency=self.supplier_currency(),
            device_id=self.device_id,
            token_guid=self.token_guid,
        )

    def _build_aero_search_params(self, search_data: dict[str, Any]) -> dict[str, Any]:
        trip = str(search_data.get("trip_type") or "oneway")
        flights: list[dict[str, Any]] = []

        if trip == "multicity":
            origins = search_data.get("from") or []
            dests = search_data.get("to") or []
            deps = search_data.get("depature") or search_data.get("departure") or []
            if not isinstance(origins, list):
                origins = [origins]
            if not isinstance(dests, list):
                dests = [dests]
            if not isinstance(deps, list):
                deps = [deps]
            for origin, dest, dep in zip(origins, dests, deps, strict=False):
                flights.append(
                    {
                        "Date": ct_norm.date_to_ct(str(dep)),
                        "IATAFrom": str(origin).upper(),
                        "IATATo": str(dest).upper(),
                    }
                )
        else:
            origin = str(search_data.get("from") or "").upper()
            dest = str(search_data.get("to") or "").upper()
            dep = str(search_data.get("depature") or search_data.get("departure") or "")
            flights.append(
                {
                    "Date": ct_norm.date_to_ct(dep),
                    "IATAFrom": origin,
                    "IATATo": dest,
                }
            )
            if trip == "return":
                ret = str(search_data.get("return") or search_data.get("return_date") or "")
                flights.append(
                    {
                        "Date": ct_norm.date_to_ct(ret),
                        "IATAFrom": dest,
                        "IATATo": origin,
                    }
                )

        return {
            "Adults": int(search_data.get("adult_config") or 1),
            "Childs": int(search_data.get("child_config") or 0),
            "Infants": int(search_data.get("infant_config") or 0),
            "FlightClass": ct_norm.flight_class_for_soap(
                str(search_data.get("cabin_class") or "Economy")
            ),
            "SearchFlights": {"SearchFlight": flights},
        }

    def _build_aero_search_api_cache_key(self, aero_search_params: dict[str, Any]) -> str:
        """Stable HTTP cache key (Mystifly-style) — hash search params, not the SOAP envelope.

        Zeep envelopes include a unique WSA MessageID per build, so ``md5(url|body)``
        never hits. Key includes currency + booking API + endpoint like Mystifly's
        ``payload|session|bookingApiId|baseUrl``.
        """
        encoded = json.dumps(aero_search_params, sort_keys=True, separators=(",", ":"), default=str)
        material = "|".join(
            [
                encoded,
                self.supplier_currency(),
                str(self.booking_api_id or "0"),
                self.endpoint_url or "",
            ]
        )
        return hashlib.sha256(material.encode()).hexdigest()

    def get_search_request(self, search_data: dict[str, Any]) -> list[HandleDescriptor]:
        if not self.credentials_ready():
            logger.warning("City Travel search skipped: credentials or EndPointUrl missing")
            return []
        aero_params = self._build_aero_search_params(search_data)
        args = {
            "credentials": self._auth_info(),
            "aeroSearchParams": aero_params,
        }
        try:
            soap = CityTravelSoap.build_request(
                "AeroSearch",
                args,
                endpoint_url=self.endpoint_url,
            )
        except Exception:
            logger.exception("City Travel failed to build AeroSearch SOAP")
            return []

        return [
            HandleDescriptor(
                url=self.endpoint_url,
                method="POST",
                body=soap.envelope,
                request_format="soap",
                headers={
                    "Content-Type": soap.content_type_with_action(),
                    "SOAPAction": f'"{soap.soap_action}"',
                },
                booking_api_id=self.booking_api_id,
                remarks="AeroSearch",
                set_cache=True,
                cache_ttl=CACHE_TTL_HTTP_SEARCH,
                cache_key=self._build_aero_search_api_cache_key(aero_params),
                timeout=60.0,
            )
        ]

    async def format_search_response(
        self,
        raw_response: Any,
        search_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        search_data = search_data or {}
        if isinstance(raw_response, dict):
            parsed = raw_response
        else:
            raw = raw_response if isinstance(raw_response, (str, bytes)) else str(raw_response or "")
            if not raw:
                return {"status": False, "data": [], "message": "Empty City Travel search response"}
            parsed = CityTravelSoap.parse_response(raw)

        result = ct_norm.extract_aero_search_result(parsed)
        if not result:
            return {"status": False, "data": [], "message": "Empty City Travel search response"}

        success = str(result.get("Success") or "").lower()
        if success in {"false", "0"}:
            return {"status": False, "data": [], "message": "City Travel search failed"}

        search_guid = str(result.get("SearchGuid") or "")
        supplier_ccy = str(result.get("Currency") or self.supplier_currency()).upper()[:3]
        rate = AdminCurrency.rate_to_admin_or_one(supplier_ccy)
        airports = ct_norm.index_airports(result)
        airlines = ct_norm.index_airlines(result)

        groups: dict[str, list[dict[str, Any]]] = {}
        for flight_data in ct_norm.flight_data_list(result):
            fp = ct_norm.itinerary_fingerprint(flight_data)
            if not fp:
                continue
            groups.setdefault(fp, []).append(flight_data)

        cheapest_rows: list[dict[str, Any]] = []
        for fingerprint, variants in groups.items():
            tier_rows: list[dict[str, Any]] = []
            for flight_data in variants:
                row = self._build_variant_row(
                    flight_data,
                    search_data=search_data,
                    search_guid=search_guid,
                    supplier_currency=supplier_ccy,
                    conversion_rate=rate,
                    airports=airports,
                    airlines=airlines,
                )
                if row is not None:
                    tier_rows.append(row)
            if not tier_rows:
                continue
            tier_rows.sort(
                key=lambda r: float((r.get("Price") or {}).get("TotalDisplayFare") or 0)
            )
            group_key = f"citytravel_group_{FlightCommon.generate_uuid()}"
            cache_put(
                group_key,
                {
                    "searchData": search_data,
                    "SearchGuid": search_guid,
                    "upsellRows": tier_rows,
                    "fingerprint": fingerprint,
                },
                CACHE_TTL_TOKEN,
            )
            cheapest = dict(tier_rows[0])
            # Search card ResultToken points at the group (UpSell loads all variants).
            cheapest["ResultToken"] = FlightCommon.encode_result_token(
                self.booking_source, group_key
            )
            cheapest_rows.append(cheapest)

        if not cheapest_rows:
            return {"status": False, "data": [], "message": "No flights found"}

        return {"status": True, "data": cheapest_rows}

    def _build_variant_row(
        self,
        flight_data: dict[str, Any],
        *,
        search_data: dict[str, Any],
        search_guid: str,
        supplier_currency: str,
        conversion_rate: float,
        airports: dict[str, dict[str, str]],
        airlines: dict[str, str],
    ) -> dict[str, Any] | None:
        offer_code = str(flight_data.get("OfferCode") or "").strip()
        if not offer_code:
            return None
        details = ct_norm.build_flight_details(
            flight_data, airports=airports, airlines=airlines
        )
        if not details:
            return None

        price = ct_norm.build_price_block(
            flight_data,
            search_data=search_data,
            conversion_rate=conversion_rate,
        )
        baggage_allowance = ct_norm.build_baggage_allowance(flight_data, search_data=search_data)
        validating = ct_norm.validating_airline(flight_data)
        offer_key = f"citytravel_offer_{FlightCommon.generate_uuid()}"
        cache_put(
            offer_key,
            {
                "SearchGuid": search_guid,
                "OfferCode": offer_code,
                "searchData": search_data,
                "flightDetails": details,
                "price": price,
                "baggageAllowance": baggage_allowance,
                "supplier_currency": supplier_currency,
                "currency_conversion_rate": conversion_rate,
                "rawFlightData": flight_data,
                "ValidatingAirline": validating,
            },
            CACHE_TTL_TOKEN,
        )

        return {
            "FlightDetails": details,
            "Price": price,
            "BaggageAllowance": baggage_allowance,
            "Attributes": {
                "IsRefundable": False,
                "BrandName": "Published",
                "fareAttributes": [],
                "fareNotes": [],
            },
            # Variant token — used after UpSell for UpdateFareQuote.
            "ResultToken": FlightCommon.encode_result_token(self.booking_source, offer_key),
        }

    async def get_upsell(self, token: str) -> dict[str, Any]:
        """Return all price variants for an itinerary group (Search ResultToken → group cache)."""
        group = cache_get(token)
        if not isinstance(group, dict):
            return {"status": False, "data": [], "message": "Invalid or expired token"}
        rows = group.get("upsellRows")
        if not isinstance(rows, list) or not rows:
            return {"status": False, "data": [], "message": "Invalid or expired token"}
        return {"status": True, "data": rows}

    def get_aero_prebook_request(self, offer_code: str, search_guid: str) -> HandleDescriptor | None:
        if not self.credentials_ready():
            return None
        args = {
            "credentials": self._auth_info(),
            "aeroPrebookParams": {
                "OfferCode": offer_code,
                "SearchGuid": search_guid,
            },
        }
        try:
            soap = CityTravelSoap.build_request(
                "AeroPrebook",
                args,
                endpoint_url=self.endpoint_url,
            )
        except Exception:
            logger.exception("City Travel failed to build AeroPrebook SOAP")
            return None
        return HandleDescriptor(
            url=self.endpoint_url,
            method="POST",
            body=soap.envelope,
            request_format="soap",
            headers={
                "Content-Type": soap.content_type_with_action(),
                "SOAPAction": f'"{soap.soap_action}"',
            },
            booking_api_id=self.booking_api_id,
            remarks="AeroPrebook",
            set_cache=False,
            timeout=60.0,
        )

    async def get_update_fare_quote(self, token: str) -> dict[str, Any]:
        offer = cache_get(token)
        if not isinstance(offer, dict):
            return {"status": False, "data": [], "message": "Invalid or expired token"}
        offer_code = str(offer.get("OfferCode") or "").strip()
        search_guid = str(offer.get("SearchGuid") or "").strip()
        if not offer_code or not search_guid:
            return {"status": False, "data": [], "message": "Invalid or expired token"}

        handle = self.get_aero_prebook_request(offer_code, search_guid)
        if handle is None:
            return {
                "status": False,
                "data": [],
                "message": "City Travel credentials or EndPointUrl missing",
            }

        try:
            results = await self._curl.execute({self.booking_source: handle})
        except Exception:
            logger.exception("City Travel AeroPrebook HTTP failed")
            return {"status": False, "data": [], "message": "AeroPrebook request failed"}

        raw = results.get(self.booking_source) or ""
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        formatted = self._format_aero_prebook_response(str(raw or ""), offer)
        if formatted is None:
            return {"status": False, "data": [], "message": "Revalidation failed"}
        return {"status": True, "data": formatted}

    def _format_aero_prebook_response(
        self,
        raw_xml: str,
        offer_cache: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not str(raw_xml or "").strip():
            return None
        parsed = CityTravelSoap.parse_response(raw_xml)
        result = ct_norm.extract_aero_prebook_result(parsed)
        if not result:
            return None
        success = str(result.get("Success") or "").lower()
        if success in {"false", "0"}:
            return None

        search_data = offer_cache.get("searchData") if isinstance(offer_cache.get("searchData"), dict) else {}
        supplier_ccy = str(
            result.get("Currency") or offer_cache.get("supplier_currency") or self.supplier_currency()
        ).upper()[:3]
        rate = AdminCurrency.rate_to_admin_or_one(supplier_ccy)
        total_supplier = ct_norm.prebook_supplier_total(result)
        if total_supplier <= 0:
            # Fall back to cached search price (supplier amounts were already converted in cache)
            prior_admin = float((offer_cache.get("price") or {}).get("TotalDisplayFare") or 0)
            if prior_admin > 0 and rate > 0:
                total_supplier = prior_admin / rate
            else:
                return None

        details = ct_norm.build_flight_details(result)
        if not details:
            details = offer_cache.get("flightDetails") if isinstance(offer_cache.get("flightDetails"), list) else []
        if not details:
            return None

        price = ct_norm.build_price_block_from_total(
            total_supplier,
            search_data=search_data,
            conversion_rate=rate,
            prior_price=offer_cache.get("price") if isinstance(offer_cache.get("price"), dict) else None,
        )
        baggage = ct_norm.build_baggage_allowance(result, search_data=search_data)
        if not baggage and isinstance(offer_cache.get("baggageAllowance"), dict):
            baggage = offer_cache["baggageAllowance"]

        offer_code = str(result.get("OfferCode") or offer_cache.get("OfferCode") or "").strip()
        search_guid = str(result.get("SearchGuid") or offer_cache.get("SearchGuid") or "").strip()
        tariffs = ct_norm.service_info_list(result.get("Tariffs"))
        services = ct_norm.service_info_list(result.get("Services"))
        lat_names = ct_norm.as_bool_flag(result.get("LatNames"))

        # Document / name flags may appear on result or first offer
        first_offer = (ct_norm.offer_infos(result) or [{}])[0]
        doc_required = ct_norm.as_bool_flag(
            result.get("DocumentsRequired") or first_offer.get("DocumentsRequired")
        )
        doc_ex_required = ct_norm.as_bool_flag(
            result.get("DocumentExDateRequired") or first_offer.get("DocumentExDateRequired")
        )
        middle_required = ct_norm.as_bool_flag(
            result.get("MiddleNameRequired") or first_offer.get("MiddleNameRequired")
        )

        quote_key = f"citytravel_fare_quote_{FlightCommon.generate_uuid()}"
        cache_put(
            quote_key,
            {
                "SearchGuid": search_guid,
                "OfferCode": offer_code,
                "searchData": search_data,
                "flightDetails": details,
                "price": price,
                "baggageAllowance": baggage,
                "supplier_currency": supplier_ccy,
                "currency_conversion_rate": rate,
                "rawPrebook": result,
                "tariffs": tariffs,
                "services": services,
                "LatNames": lat_names,
                "DocumentsRequired": doc_required,
                "DocumentExDateRequired": doc_ex_required,
                "MiddleNameRequired": middle_required,
                "FullPrice": total_supplier,
                "offerCacheKey": None,
            },
            CACHE_TTL_TOKEN,
        )

        return {
            "FlightDetails": details,
            "Price": price,
            "BaggageAllowance": baggage,
            "Attributes": {
                "IsRefundable": False,
                "BrandName": "Published",
                "fareAttributes": [],
                "fareNotes": [],
                "LatNames": lat_names,
                "DocumentsRequired": doc_required,
                "DocumentExDateRequired": doc_ex_required,
                "MiddleNameRequired": middle_required,
            },
            "ResultToken": FlightCommon.encode_result_token(self.booking_source, quote_key),
        }

    async def get_extra_services(self, token: str) -> dict[str, Any]:
        """Format AeroPrebook ``Services`` from fare-quote cache (no SOAP)."""
        quote = cache_get(token)
        if not isinstance(quote, dict):
            return {"status": False, "data": [], "message": "Invalid or expired token"}
        details = quote.get("flightDetails")
        if not isinstance(details, list) or not details:
            return {"status": False, "data": [], "message": "Invalid or expired token"}

        services = quote.get("services")
        if not isinstance(services, list):
            services = ct_norm.service_info_list(
                (quote.get("rawPrebook") or {}).get("Services")
                if isinstance(quote.get("rawPrebook"), dict)
                else None
            )

        rate = float(quote.get("currency_conversion_rate") or 1.0)
        if rate <= 0:
            rate = 1.0
        formatted = ct_norm.format_extra_services_for_api(
            [s for s in services if isinstance(s, dict)],
            flight_details=details,
            conversion_rate=rate,
            admin_currency=AdminCurrency.code() or "USD",
        )
        return {
            "status": True,
            "data": {"ExtraServiceDetails": formatted},
        }

    async def get_flight_row_from_token_for_pricing(self, token: str) -> dict[str, Any]:
        """Build a FlightDetails/Price row from fare-quote (or offer) cache — no SOAP."""
        cached = cache_get(token)
        if not isinstance(cached, dict):
            return {"status": False, "data": [], "message": "Invalid or expired token"}

        details = cached.get("flightDetails")
        if not isinstance(details, list):
            details = cached.get("FlightDetails")
        price = cached.get("price")
        if not isinstance(price, dict):
            price = cached.get("Price")
        if not isinstance(details, list) or not details or not isinstance(price, dict):
            return {"status": False, "data": [], "message": "Invalid or expired token"}

        baggage = cached.get("baggageAllowance")
        if not isinstance(baggage, dict):
            baggage = cached.get("BaggageAllowance") if isinstance(cached.get("BaggageAllowance"), dict) else {}

        attrs = cached.get("Attributes") if isinstance(cached.get("Attributes"), dict) else {
            "IsRefundable": False,
            "BrandName": "Published",
            "fareAttributes": [],
            "fareNotes": [],
            "LatNames": bool(cached.get("LatNames")),
            "DocumentsRequired": bool(cached.get("DocumentsRequired")),
            "DocumentExDateRequired": bool(cached.get("DocumentExDateRequired")),
            "MiddleNameRequired": bool(cached.get("MiddleNameRequired")),
        }

        return {
            "status": True,
            "data": {
                "FlightDetails": details,
                "Price": copy.deepcopy(price),
                "BaggageAllowance": baggage,
                "Attributes": attrs,
            },
            "message": "Success",
        }

    async def get_pre_book_data(
        self,
        token: str,
        app_reference: str,
        passengers: list[dict[str, Any]],
        *,
        selected_services: list[Any] | None = None,
        selected_tariffs: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Cache fare-quote + pax under ``citytravel_pre_book_*`` (no AeroBook)."""
        quote = cache_get(token)
        if not isinstance(quote, dict):
            return {"status": False, "data": [], "message": "Invalid or expired token"}
        offer_code = str(quote.get("OfferCode") or "").strip()
        search_guid = str(quote.get("SearchGuid") or "").strip()
        if not offer_code or not search_guid:
            return {"status": False, "data": [], "message": "Invalid or expired token"}

        details = quote.get("flightDetails")
        if not isinstance(details, list) or not details:
            return {"status": False, "data": [], "message": "Invalid token"}
        price = quote.get("price") if isinstance(quote.get("price"), dict) else None
        if not price:
            return {"status": False, "data": [], "message": "Invalid token"}

        if not passengers:
            return {"status": False, "data": [], "message": "Passenger details are required"}
        lead = passengers[0] if isinstance(passengers[0], dict) else {}
        if not str(lead.get("Email") or lead.get("email") or "").strip():
            return {"status": False, "data": [], "message": "Lead passenger email is required"}
        if not str(lead.get("ContactNo") or lead.get("phone") or "").strip():
            return {
                "status": False,
                "data": [],
                "message": "Lead passenger contact number is required",
            }

        docs_required = bool(quote.get("DocumentsRequired"))
        doc_ex_required = bool(quote.get("DocumentExDateRequired"))
        middle_required = bool(quote.get("MiddleNameRequired"))
        for idx, pax in enumerate(passengers):
            if not isinstance(pax, dict):
                return {"status": False, "data": [], "message": f"Invalid passenger at position {idx + 1}"}
            if docs_required:
                doc = str(
                    pax.get("PassportNumber")
                    or pax.get("DocumentNumber")
                    or pax.get("passport_number")
                    or ""
                ).strip()
                if not doc:
                    return {
                        "status": False,
                        "data": [],
                        "message": f"Document number is required for passenger {idx + 1}",
                    }
            if doc_ex_required:
                exp = str(
                    pax.get("PassportExpiry")
                    or pax.get("DocumentExpiry")
                    or pax.get("passport_expiry")
                    or ""
                ).strip()
                if not exp:
                    return {
                        "status": False,
                        "data": [],
                        "message": f"Document expiry is required for passenger {idx + 1}",
                    }
            if middle_required:
                mid = str(pax.get("MiddleName") or pax.get("middle_name") or "").strip()
                if not mid:
                    return {
                        "status": False,
                        "data": [],
                        "message": f"Middle name is required for passenger {idx + 1}",
                    }

        row_attrs = {
            "IsRefundable": False,
            "BrandName": "Published",
            "fareAttributes": [],
            "fareNotes": [],
            "LatNames": bool(quote.get("LatNames")),
            "DocumentsRequired": docs_required,
            "DocumentExDateRequired": doc_ex_required,
            "MiddleNameRequired": middle_required,
        }
        baggage = quote.get("baggageAllowance") if isinstance(quote.get("baggageAllowance"), dict) else {}

        pre_book_key = f"citytravel_pre_book_{FlightCommon.generate_uuid()}"
        cache_put(
            pre_book_key,
            {
                **quote,
                "pax_details": {"Passengers": passengers},
                "app_reference": app_reference,
                "SelectedServices": list(selected_services or []),
                "SelectedTariffs": list(selected_tariffs or []),
                "fareQuoteToken": token,
            },
            CACHE_TTL_TOKEN,
        )

        row = {
            "FlightDetails": details,
            "Price": price,
            "BaggageAllowance": baggage,
            "Attributes": row_attrs,
            "ResultToken": FlightCommon.encode_result_token(self.booking_source, pre_book_key),
            "app_reference": app_reference,
        }
        return {"status": True, "data": row}

    async def hold_ticket(self, request: dict[str, Any]) -> dict[str, Any]:
        """AeroBook — create reservation using pre-book cache (ClientReference = app_reference)."""
        token = str(request.get("ResultToken") or request.get("resultToken") or "").strip()
        decoded = FlightCommon.decode_result_token(token) if token else None
        if not decoded:
            return {"status": False, "data": [], "message": "Invalid ResultToken"}

        pre = cache_get(str(decoded["token"]))
        if not isinstance(pre, dict):
            return {"status": False, "data": [], "message": "Invalid or expired pre-book token"}

        app_reference = str(
            pre.get("app_reference")
            or request.get("app_reference")
            or request.get("AppReference")
            or ""
        ).strip()
        offer_code = str(pre.get("OfferCode") or "").strip()
        search_guid = str(pre.get("SearchGuid") or "").strip()
        if not app_reference or not offer_code or not search_guid:
            return {"status": False, "data": [], "message": "Pre-book session is incomplete"}

        pax_details = pre.get("pax_details") if isinstance(pre.get("pax_details"), dict) else {}
        passengers = pax_details.get("Passengers") if isinstance(pax_details.get("Passengers"), list) else []
        if not passengers:
            return {"status": False, "data": [], "message": "Passenger details are required"}

        lead = passengers[0] if isinstance(passengers[0], dict) else {}
        email = str(lead.get("Email") or lead.get("email") or "").strip()
        phone = str(lead.get("ContactNo") or lead.get("phone") or "").strip()
        if not email or not phone:
            return {
                "status": False,
                "data": [],
                "message": "Lead passenger email and phone are required",
            }

        selected_services = pre.get("SelectedServices") if isinstance(pre.get("SelectedServices"), list) else []
        selected_tariffs = pre.get("SelectedTariffs") if isinstance(pre.get("SelectedTariffs"), list) else []
        if isinstance(request.get("SelectedServices"), list):
            selected_services = request["SelectedServices"]
        if isinstance(request.get("SelectedTariffs"), list):
            selected_tariffs = request["SelectedTariffs"]

        if not self.credentials_ready():
            return {
                "status": False,
                "data": [],
                "message": "City Travel credentials or EndPointUrl missing",
            }

        pax_list = [self._map_pax_for_aero_book(p) for p in passengers if isinstance(p, dict)]
        customer_fio = (
            f"{lead.get('FirstName') or lead.get('first_name') or ''} "
            f"{lead.get('LastName') or lead.get('last_name') or ''}"
        ).strip() or None

        aero_book_params: dict[str, Any] = {
            "OfferCode": offer_code,
            "SearchGuid": search_guid,
            "Email": email,
            "Phone": phone,
            "ClientReference": app_reference[:40],
            "CustomerFIO": customer_fio,
            "PaxList": {"PaxData": pax_list},
        }
        if selected_tariffs:
            aero_book_params["SelectedTariffs"] = {"string": [str(x) for x in selected_tariffs]}
        if selected_services:
            aero_book_params["SelectedServices"] = {"string": [str(x) for x in selected_services]}

        handle = self._soap_handle(
            "AeroBook",
            {"credentials": self._auth_info(), "aeroBookParams": aero_book_params},
            remarks="AeroBook",
            timeout=90.0,
        )
        if handle is None:
            return {"status": False, "data": [], "message": "Failed to build AeroBook request"}

        raw = await self._execute_raw(handle)
        result = ct_norm.extract_aero_book_result(
            CityTravelSoap.parse_response(raw) if raw else {}
        )
        success = str(result.get("Success") or "").lower()
        if not result or success in {"false", "0"}:
            # Timeout / ambiguous failure — recover via ClientReference.
            recovered = await self._recover_book_by_client_reference(app_reference)
            if recovered is None:
                return {
                    "status": False,
                    "data": [],
                    "message": "AeroBook failed",
                }
            result = recovered

        book_id = str(result.get("BookId") or "").strip()
        book_guid = str(result.get("BookGuid") or "").strip()
        if not book_id:
            return {"status": False, "data": [], "message": "AeroBook did not return BookId"}

        full_price = ct_norm._as_float(result.get("FullPrice"))
        gdspnr = ct_norm.first_pnr_from_offers(result)
        details = ct_norm.build_flight_details(result)
        if not details:
            details = pre.get("flightDetails") if isinstance(pre.get("flightDetails"), list) else []
        price = pre.get("price") if isinstance(pre.get("price"), dict) else {}
        supplier_ccy = str(
            result.get("Currency") or pre.get("supplier_currency") or self.supplier_currency()
        ).upper()[:3]
        rate = AdminCurrency.rate_to_admin_or_one(supplier_ccy)
        if full_price > 0:
            price = ct_norm.build_price_block_from_total(
                full_price,
                search_data=pre.get("searchData") if isinstance(pre.get("searchData"), dict) else {},
                conversion_rate=rate,
            )

        hold_data = {
            "app_reference": app_reference,
            "bookingId": book_id,
            "booking_id": book_id,
            "book_guid": book_guid,
            "BookGuid": book_guid,
            "gdspnr": gdspnr,
            "hold_time": str(result.get("ConfirmableTo") or ""),
            "FlightDetails": details,
            "Price": price,
            "BaggageAllowance": pre.get("baggageAllowance")
            if isinstance(pre.get("baggageAllowance"), dict)
            else {},
            "Attributes": {
                "IsRefundable": False,
                "BrandName": "Published",
                "DocumentsRequired": bool(pre.get("DocumentsRequired")),
                "DocumentExDateRequired": bool(pre.get("DocumentExDateRequired")),
                "MiddleNameRequired": bool(pre.get("MiddleNameRequired")),
                "LatNames": bool(pre.get("LatNames")),
            },
            "Attr": {
                "holdAllowed": True,
                "supplier": self.booking_source,
                "book_price": full_price,
                "supplier_currency": supplier_ccy,
            },
            "RawBook": result,
            "ResultToken": token,
        }

        cache_put(
            f"citytravel_booking_{book_id}",
            {
                **hold_data,
                "OfferCode": offer_code,
                "SearchGuid": search_guid,
                "pre_book_token": str(decoded["token"]),
            },
            CACHE_TTL_TOKEN,
        )
        return {"status": True, "data": hold_data, "message": "Booking held"}

    async def issue_ticket(self, locator: str) -> dict[str, Any]:
        """ConfirmBook — ticket a held booking (locator = BookId)."""
        book_id = str(locator or "").strip()
        if not book_id:
            return {"status": False, "data": [], "message": "BookId is required"}

        cached = cache_get(f"citytravel_booking_{book_id}")
        cached = cached if isinstance(cached, dict) else {}
        book_guid = str(cached.get("book_guid") or cached.get("BookGuid") or "").strip()
        attr = cached.get("Attr") if isinstance(cached.get("Attr"), dict) else {}
        price = ct_norm._as_float(attr.get("book_price"))
        if price <= 0:
            price = ct_norm._as_float((cached.get("Price") or {}).get("TotalDisplayFare"))
            rate = AdminCurrency.rate_to_admin_or_one(
                str(attr.get("supplier_currency") or self.supplier_currency())
            )
            if price > 0 and rate > 0:
                # ConfirmBook wants supplier currency amount; invert if we only have admin.
                # Prefer RawBook FullPrice.
                raw_book = cached.get("RawBook") if isinstance(cached.get("RawBook"), dict) else {}
                price = ct_norm._as_float(raw_book.get("FullPrice")) or (price / rate)

        if not book_guid:
            return {"status": False, "data": [], "message": "BookGuid missing for ConfirmBook"}
        if price <= 0:
            return {"status": False, "data": [], "message": "Book price missing for ConfirmBook"}
        if not self.credentials_ready():
            return {
                "status": False,
                "data": [],
                "message": "City Travel credentials or EndPointUrl missing",
            }

        handle = self._soap_handle(
            "ConfirmBook",
            {
                "authInfo": self._auth_info(),
                "confirmParams": {
                    "BookId": int(book_id) if book_id.isdigit() else book_id,
                    "BookGuid": book_guid,
                    "Price": price,
                },
            },
            remarks="ConfirmBook",
            timeout=90.0,
        )
        if handle is None:
            return {"status": False, "data": [], "message": "Failed to build ConfirmBook request"}

        raw = await self._execute_raw(handle)
        order = ct_norm.extract_confirm_book_result(
            CityTravelSoap.parse_response(raw) if raw else {}
        )
        if not order:
            return {"status": False, "data": [], "message": "ConfirmBook failed"}

        booking_status = str(order.get("BookingStatus") or "").strip()
        gdspnr = ct_norm.first_pnr_from_offers(order) or str(cached.get("gdspnr") or "")
        tickets = ct_norm.ticket_passengers_from_order(order)
        pending = booking_status.lower() in {"waittobooking", "wait_to_booking"}
        cancelled = booking_status.lower() in {"cancelled", "canceled"}

        if cancelled:
            return {
                "status": False,
                "data": {"bookingId": book_id, "gdspnr": gdspnr, "RawConfirm": order},
                "message": "Ticketing cancelled by supplier",
            }

        data: dict[str, Any] = {
            "bookingId": book_id,
            "book_guid": book_guid,
            "gdspnr": gdspnr,
            "BookingStatus": booking_status,
            "Passengers": tickets,
            "RawConfirm": order,
            "app_reference": cached.get("app_reference"),
        }
        if pending:
            data["confirmationPending"] = True

        cache_put(
            f"citytravel_booking_{book_id}",
            {**cached, "ticketing": data, "RawConfirm": order, "gdspnr": gdspnr},
            CACHE_TTL_TOKEN,
        )
        return {"status": True, "data": data, "message": "Ticketed" if not pending else "Ticketing pending"}

    async def refresh_booking_from_supplier(
        self, locator: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """OrderInfo poll for WaitToBooking / status refresh."""
        book_id = str(locator or "").strip()
        context = context or {}
        cached = cache_get(f"citytravel_booking_{book_id}") if book_id else None
        cached = cached if isinstance(cached, dict) else {}
        book_guid = str(
            context.get("book_guid")
            or cached.get("book_guid")
            or cached.get("BookGuid")
            or ""
        ).strip()
        app_reference = str(context.get("app_reference") or cached.get("app_reference") or "").strip()

        if not self.credentials_ready():
            return {
                "status": False,
                "message": "City Travel credentials or EndPointUrl missing",
                "outcome": "failed",
                "data": [],
            }

        params: dict[str, Any]
        if book_id and book_guid:
            params = {
                "BookId": int(book_id) if book_id.isdigit() else book_id,
                "BookGuid": book_guid,
            }
        elif app_reference:
            today = timeutils.datetime_now().strftime("%d.%m.%Y")
            params = {
                "BookId": 0,
                "BookGuid": "00000000-0000-0000-0000-000000000000",
                "SearchFilter": {
                    "ClientReference": app_reference[:40],
                    "DateFrom": today,
                    "DateTo": today,
                },
            }
        else:
            return {
                "status": False,
                "message": "BookId/BookGuid or app_reference required",
                "outcome": "failed",
                "data": [],
            }

        handle = self._soap_handle(
            "OrderInfo",
            {"credentials": self._auth_info(), "orderInfoParams": params},
            remarks="OrderInfo",
            timeout=60.0,
        )
        if handle is None:
            return {
                "status": False,
                "message": "Failed to build OrderInfo request",
                "outcome": "failed",
                "data": [],
            }

        raw = await self._execute_raw(handle)
        order = ct_norm.extract_order_info_result(
            CityTravelSoap.parse_response(raw) if raw else {}
        )
        if not order:
            return {
                "status": False,
                "message": "OrderInfo failed",
                "outcome": "failed",
                "data": [],
            }

        booking_status = str(order.get("BookingStatus") or "").strip()
        status_l = booking_status.lower()
        gdspnr = ct_norm.first_pnr_from_offers(order)
        tickets = ct_norm.ticket_passengers_from_order(order)
        book_id_out = str(order.get("BookId") or book_id).strip()
        book_guid_out = str(order.get("BookGuid") or book_guid).strip()

        if status_l in {"cancelled", "canceled"}:
            outcome = "failed"
        elif status_l in {"waittobooking", "wait_to_booking"}:
            outcome = "pending"
        elif status_l in {"booked", "ticketed"} or tickets:
            outcome = "confirmed"
        else:
            outcome = "pending"

        data = {
            "app_reference": app_reference or cached.get("app_reference"),
            "bookingId": book_id_out,
            "book_guid": book_guid_out,
            "gdspnr": gdspnr,
            "BookingStatus": booking_status,
            "ticketing": {"Passengers": tickets, "BookingStatus": booking_status},
            "Attr": {
                "confirmationPending": outcome == "pending",
            },
            "RawOrderInfo": order,
            "FlightDetails": cached.get("FlightDetails") or [],
            "Price": cached.get("Price") or {},
        }
        if book_id_out:
            cache_put(
                f"citytravel_booking_{book_id_out}",
                {**cached, **data},
                CACHE_TTL_TOKEN,
            )
        return {
            "status": True,
            "message": "Status updated",
            "outcome": outcome,
            "data": data,
        }

    async def cancel_booking(
        self, locator: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """OrderInfo eligibility check → AnnulateBook (VOID / cancel)."""
        context = context or {}
        book_id = str(locator or "").strip()
        book_guid = str(context.get("book_guid") or context.get("BookGuid") or "").strip()
        app_reference = str(context.get("app_reference") or "").strip()

        if not self.credentials_ready():
            return {
                "status": False,
                "message": "City Travel credentials or EndPointUrl missing",
                "data": [],
            }
        if not book_id or not book_guid:
            return {
                "status": False,
                "message": "BookId and BookGuid are required to cancel",
                "data": [],
            }

        # 1) Fresh OrderInfo — status + Cancellable / DeadLineDateUtc
        order_info = await self.refresh_booking_from_supplier(
            book_id,
            {
                "book_guid": book_guid,
                "app_reference": app_reference,
            },
        )
        if not order_info.get("status"):
            return {
                "status": False,
                "message": order_info.get("message") or "OrderInfo failed before cancel",
                "data": [],
            }

        order = (
            order_info["data"].get("RawOrderInfo")
            if isinstance(order_info.get("data"), dict)
            else None
        )
        order = order if isinstance(order, dict) else {}
        booking_status = str(
            order.get("BookingStatus")
            or (order_info["data"].get("BookingStatus") if isinstance(order_info.get("data"), dict) else "")
            or ""
        ).strip()
        status_l = booking_status.lower()
        book_id_out = str(order.get("BookId") or book_id).strip()
        book_guid_out = str(order.get("BookGuid") or book_guid).strip()

        if status_l in {"cancelled", "canceled"}:
            return {
                "status": True,
                "message": "Booking is already cancelled at supplier",
                "already_cancelled": True,
                "data": {
                    "app_reference": app_reference,
                    "bookingId": book_id_out,
                    "book_guid": book_guid_out,
                    "BookingStatus": booking_status,
                    "RawOrderInfo": order,
                },
            }

        tickets = ct_norm.ticket_passengers_from_order(order)
        tickets_issued = bool(tickets)
        cancellable = ct_norm.soap_flag_true(order.get("Cancellable"))
        deadline = ct_norm.void_deadline_utc(order)
        now = timeutils.datetime_now()

        # CT rules: hold without tickets → always cancellable; ticketed → VOID if Cancellable
        # and before DeadLineDateUtc.
        if tickets_issued:
            if not cancellable:
                return {
                    "status": False,
                    "message": "Booking is not cancellable (Cancellable=false on OrderInfo)",
                    "data": {
                        "BookingStatus": booking_status,
                        "Cancellable": False,
                        "DeadLineDateUtc": order.get("DeadLineDateUtc"),
                        "tickets_issued": True,
                    },
                }
            if deadline is not None and now > deadline:
                return {
                    "status": False,
                    "message": (
                        f"VOID deadline has passed "
                        f"({order.get('DeadLineDateUtc') or order.get('DeadLineDate')})"
                    ),
                    "data": {
                        "BookingStatus": booking_status,
                        "Cancellable": True,
                        "DeadLineDateUtc": order.get("DeadLineDateUtc"),
                        "tickets_issued": True,
                    },
                }

        # 2) AnnulateBook
        handle = self._soap_handle(
            "AnnulateBook",
            {
                "credentials": self._auth_info(),
                "annulateBookParams": {
                    "BookId": int(book_id_out) if book_id_out.isdigit() else book_id_out,
                    "BookGuid": book_guid_out,
                },
            },
            remarks="AnnulateBook",
            timeout=90.0,
        )
        if handle is None:
            return {
                "status": False,
                "message": "Failed to build AnnulateBook request",
                "data": [],
            }

        raw = await self._execute_raw(handle)
        result = ct_norm.extract_annulate_book_result(
            CityTravelSoap.parse_response(raw) if raw else {}
        )
        success = ct_norm.soap_flag_true(result.get("Success")) if result else False
        if not success:
            err = (
                str(result.get("ErrorDescription") or result.get("Message") or "").strip()
                if result
                else ""
            )
            return {
                "status": False,
                "message": err or "AnnulateBook failed",
                "data": {"RawAnnulate": result or {}, "RawOrderInfo": order},
            }

        data = {
            "app_reference": app_reference,
            "bookingId": book_id_out,
            "book_guid": book_guid_out,
            "BookingStatus": "Cancelled",
            "Cancellable": cancellable,
            "DeadLineDateUtc": order.get("DeadLineDateUtc"),
            "tickets_issued": tickets_issued,
            "RawOrderInfo": order,
            "RawAnnulate": result,
        }
        if book_id_out:
            cached = cache_get(f"citytravel_booking_{book_id_out}")
            cached = cached if isinstance(cached, dict) else {}
            cache_put(
                f"citytravel_booking_{book_id_out}",
                {**cached, **data, "cancelled": True},
                CACHE_TTL_TOKEN,
            )
        return {"status": True, "message": "Booking cancelled", "data": data}

    def _soap_handle(
        self,
        operation: str,
        args: dict[str, Any],
        *,
        remarks: str,
        timeout: float = 60.0,
    ) -> HandleDescriptor | None:
        try:
            soap = CityTravelSoap.build_request(
                operation,
                args,
                endpoint_url=self.endpoint_url,
            )
        except Exception:
            logger.exception("City Travel failed to build %s SOAP", operation)
            return None
        return HandleDescriptor(
            url=self.endpoint_url,
            method="POST",
            body=soap.envelope,
            request_format="soap",
            headers={
                "Content-Type": soap.content_type_with_action(),
                "SOAPAction": f'"{soap.soap_action}"',
            },
            booking_api_id=self.booking_api_id,
            remarks=remarks,
            set_cache=False,
            timeout=timeout,
        )

    async def _execute_raw(self, handle: HandleDescriptor) -> str:
        try:
            results = await self._curl.execute({self.booking_source: handle})
        except Exception:
            logger.exception("City Travel SOAP HTTP failed (%s)", handle.remarks)
            return ""
        raw = results.get(self.booking_source) or ""
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        return str(raw or "")

    async def _recover_book_by_client_reference(
        self, app_reference: str
    ) -> dict[str, Any] | None:
        """OrderInfo recovery after AeroBook timeout / ambiguous failure."""
        today = timeutils.datetime_now().strftime("%d.%m.%Y")
        handle = self._soap_handle(
            "OrderInfo",
            {
                "credentials": self._auth_info(),
                "orderInfoParams": {
                    "BookId": 0,
                    "BookGuid": "00000000-0000-0000-0000-000000000000",
                    "SearchFilter": {
                        "ClientReference": app_reference[:40],
                        "DateFrom": today,
                        "DateTo": today,
                    },
                },
            },
            remarks="OrderInfo-recover",
            timeout=60.0,
        )
        if handle is None:
            return None
        raw = await self._execute_raw(handle)
        order = ct_norm.extract_order_info_result(
            CityTravelSoap.parse_response(raw) if raw else {}
        )
        if not order or not str(order.get("BookId") or "").strip():
            return None
        # Shape like AeroBook result for downstream mapping.
        return {
            "Success": True,
            "BookId": order.get("BookId"),
            "BookGuid": order.get("BookGuid"),
            "FullPrice": (order.get("Price") or {}).get("Value")
            if isinstance(order.get("Price"), dict)
            else order.get("Price"),
            "Offers": order.get("MultiGatesInfo") or order.get("Offers"),
            "ConfirmableTo": order.get("ConfirmableTo") or order.get("DeadLineDate"),
            "PaxList": order.get("PaxDataList") or order.get("PaxList"),
            "SearchGuid": order.get("SearchGuid"),
            "Currency": (
                (order.get("Price") or {}).get("Currency")
                if isinstance(order.get("Price"), dict)
                else None
            ),
            "_recovered_from_order_info": True,
        }

    @staticmethod
    def _map_pax_for_aero_book(pax: dict[str, Any]) -> dict[str, Any]:
        raw_type = str(pax.get("PaxType") or pax.get("PassengerType") or "Adult").strip().upper()
        if raw_type in {"CHD", "CHILD"}:
            age_type = "Child"
        elif raw_type in {"INF", "INFANT"}:
            age_type = "Infant"
        else:
            age_type = "Adult"

        title = str(pax.get("Title") or pax.get("title") or "").strip()
        gender_code = FlightCommon.gender_code_from_title(pax)
        gender = "Female" if gender_code == "F" else "Male"
        # Honor explicit Gender when present.
        g_raw = str(pax.get("Gender") or pax.get("GenderType") or "").strip().lower()
        if g_raw in {"f", "female"}:
            gender = "Female"
        elif g_raw in {"m", "male"}:
            gender = "Male"
        elif title:
            gender = "Female" if gender_code == "F" else "Male"

        dob = str(pax.get("DateOfBirth") or pax.get("dob") or "").strip()
        nationality = get_country_service().to_iso3(
            str(pax.get("Nationality") or pax.get("nationality") or ""),
            default="IND",
        )
        doc = str(
            pax.get("PassportNumber")
            or pax.get("DocumentNumber")
            or pax.get("passport_number")
            or ""
        ).strip()
        doc_ex = str(
            pax.get("PassportExpiry")
            or pax.get("DocumentExpiry")
            or pax.get("passport_expiry")
            or ""
        ).strip()
        middle = str(pax.get("MiddleName") or pax.get("middle_name") or "").strip() or None

        row: dict[str, Any] = {
            "AgeType": age_type,
            "BirthDay": ct_norm.date_to_ct(dob),
            "BirthISO": nationality,
            "GenderType": gender,
            "Name": str(pax.get("FirstName") or pax.get("first_name") or "").strip(),
            "Surname": str(pax.get("LastName") or pax.get("last_name") or "").strip(),
            "MiddleName": middle,
        }
        if doc:
            row["Document"] = doc
        if doc_ex:
            row["DocumentExDate"] = ct_norm.date_to_ct(doc_ex)
        return row
