"""City Travel flight provider — Search through PreBook (pay-then-hold draft)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.flight.infrastructure.citytravel import normalize as ct_norm
from luxtj.contexts.flight.infrastructure.citytravel.soap import CityTravelSoap
from luxtj.contexts.flight.infrastructure.token_cache import cache_get, cache_put
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.shared_kernel.infrastructure.http import HandleDescriptor, MultiHttpClient

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
        # TODO: Build price row from group/offer/fare-quote cache (no SOAP).
        _ = token
        return {}

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
        # TODO: AeroBook (hold) using ClientReference = app_reference.
        _ = request
        return self._todo("hold_ticket", "AeroBook")

    async def issue_ticket(self, locator: str) -> dict[str, Any]:
        # TODO: ConfirmBook using stored BookId / BookGuid / price.
        _ = locator
        return self._todo("issue_ticket", "ConfirmBook")

    async def refresh_booking_from_supplier(
        self, locator: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # TODO: OrderInfo by BookId / BookGuid.
        _ = (locator, context)
        return self._todo("refresh_booking_from_supplier", "OrderInfo")
