"""City Travel flight provider — live Search (Phase 5); later steps still stubs."""

from __future__ import annotations

import logging
from typing import Any

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.flight.infrastructure.citytravel import normalize as ct_norm
from luxtj.contexts.flight.infrastructure.citytravel.soap import CityTravelSoap
from luxtj.contexts.flight.infrastructure.token_cache import cache_put
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.shared_kernel.infrastructure.http import HandleDescriptor

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED = "not implemented yet"
CACHE_TTL_TOKEN = 45 * 60
CACHE_TTL_HTTP_SEARCH = 900


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
    ) -> None:
        cfg = config or {}
        configs = cfg.get("configs") if isinstance(cfg.get("configs"), dict) else cfg
        self.config = configs if isinstance(configs, dict) else {}
        self.booking_api_id = booking_api_id
        self._session = session
        self._http = http_client

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

    def get_search_request(self, search_data: dict[str, Any]) -> list[HandleDescriptor]:
        if not self.credentials_ready():
            logger.warning("City Travel search skipped: credentials or EndPointUrl missing")
            return []
        args = {
            "credentials": self._auth_info(),
            "aeroSearchParams": self._build_aero_search_params(search_data),
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
        admin_ccy = AdminCurrency.code()
        rate = AdminCurrency.rate_to_admin_or_one(supplier_ccy)

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
                    admin_currency=admin_ccy,
                    conversion_rate=rate,
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
        admin_currency: str,
        conversion_rate: float,
    ) -> dict[str, Any] | None:
        offer_code = str(flight_data.get("OfferCode") or "").strip()
        if not offer_code:
            return None
        details = ct_norm.build_flight_details(flight_data)
        if not details:
            return None

        price = ct_norm.build_price_block(
            flight_data,
            search_data=search_data,
            supplier_currency=supplier_currency,
            admin_currency=admin_currency,
            conversion_rate=conversion_rate,
        )
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
                "rawFlightData": flight_data,
            },
            CACHE_TTL_TOKEN,
        )

        bag_hint = ""
        for leg in details:
            for seg in leg:
                bag = (seg.get("Attr") or {}).get("Baggage")
                if bag:
                    bag_hint = str(bag)
                    break
            if bag_hint:
                break

        return {
            "FlightDetails": details,
            "Price": price,
            "Attr": {
                "IsRefundable": 0,
                "AirlineRemark": validating,
                "BrandName": bag_hint or offer_code,
                "IsLCC": ct_norm.is_lcc(flight_data),
                "fareAttributes": [],
                "fareNotes": [],
                "OfferCode": offer_code,
            },
            "HoldTicket": True,
            # Variant token — used after UpSell for UpdateFareQuote.
            "ResultToken": FlightCommon.encode_result_token(self.booking_source, offer_key),
            "APIIDENTIFY": self.booking_source,
        }

    async def get_upsell(self, token: str) -> dict[str, Any]:
        # TODO(Phase 6): Load citytravel_group_* cache; return all upsellRows (no SOAP).
        _ = token
        return self._todo("get_upsell", "return cached price variants for itinerary group")

    async def get_update_fare_quote(self, token: str) -> dict[str, Any]:
        # TODO(Phase 7): Resolve offer token → AeroPrebook → citytravel_fare_quote_* cache.
        _ = token
        return self._todo("get_update_fare_quote", "AeroPrebook revalidate")

    async def get_extra_services(self, token: str) -> dict[str, Any]:
        # TODO(Phase 8): Map Services from fare-quote cache → seats/bags/meals shape.
        _ = token
        return self._todo("get_extra_services", "services from AeroPrebook cache")

    async def get_flight_row_from_token_for_pricing(self, token: str) -> dict[str, Any]:
        # TODO: Build price row from group/offer/fare-quote cache (no SOAP).
        _ = token
        return {}

    async def get_pre_book_data(
        self,
        token: str,
        app_reference: str,
        passengers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        # TODO(Phase 9): Cache pax + app_reference under citytravel_pre_book_* (no AeroBook).
        _ = (token, app_reference, passengers)
        return self._todo("get_pre_book_data", "PreBook cache only")

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
