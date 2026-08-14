"""Flight blender — orchestration (City Travel provider registered; methods filled later)."""

from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.currency.domain.booking_money_for_client import BookingMoneyForClient
from luxtj.contexts.flight.application.markup import FlightMarkup
from luxtj.contexts.flight.application.prebook_quote import FlightPreBookQuote
from luxtj.contexts.flight.application.promo import FlightPromo
from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.flight.domain.provider import FlightProvider
from luxtj.contexts.flight.infrastructure.booking_persistence import persist_pre_book
from luxtj.contexts.flight.infrastructure.citytravel.provider import CityTravelFlightProvider
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import (
    FlightBookingDetailsRow,
    FlightBookingItineraryDetailsRow,
    FlightBookingPassengerDetailsRow,
    FlightBookingTransactionDetailsRow,
    FlightSearchRow,
)
from luxtj.contexts.flight.infrastructure.token_cache import cache_get
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.contexts.payment.application.service import PaymentGatewayService
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPaymentGatewayTransactionRepository,
)
from luxtj.shared_kernel.infrastructure.http import MultiHttpClient
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)
_SEARCH_DONE = object()


class FlightBlender:
    def __init__(
        self,
        session: AsyncSession,
        *,
        http_client: Any | None = None,
        multi_http: MultiHttpClient | None = None,
        flight_markup: FlightMarkup | None = None,
    ) -> None:
        self._session = session
        self._http = http_client
        self._curl = multi_http or MultiHttpClient(http_client, session=session)
        self._markup = flight_markup or FlightMarkup(session)

    @staticmethod
    def _round_amount(amount: float) -> float:
        return round(float(amount), 2)

    @staticmethod
    def _first_last_segments(
        flight: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        details = flight.get("FlightDetails")
        if not isinstance(details, list) or not details:
            return None
        first_leg = details[0]
        if not isinstance(first_leg, list) or not first_leg or not isinstance(first_leg[0], dict):
            return None
        last_leg = details[-1] if isinstance(details[-1], list) and details[-1] else first_leg
        last_seg = last_leg[-1] if isinstance(last_leg[-1], dict) else first_leg[0]
        return first_leg[0], last_seg

    def _markup_params_from_flight(self, flight: dict[str, Any]) -> dict[str, Any] | None:
        segs = self._first_last_segments(flight)
        if segs is None:
            return None
        first_seg, last_seg = segs
        origin = first_seg.get("Origin") if isinstance(first_seg.get("Origin"), dict) else {}
        dest = last_seg.get("Destination") if isinstance(last_seg.get("Destination"), dict) else {}
        airline = (
            first_seg.get("OperatorCode")
            or first_seg.get("MarketingAirlineCode")
            or first_seg.get("OperatingAirlineCode")
            or ""
        )
        return {
            "airline": str(airline or ""),
            "origin": str(origin.get("AirportCode") or ""),
            "destination": str(dest.get("AirportCode") or ""),
            "cabinClass": str(first_seg.get("CabinClass") or ""),
            "travelDate": str(origin.get("date") or ""),
        }

    async def set_flight_markup(self, flight: dict[str, Any]) -> float:
        """
        Embed admin markup into Tax / TotalDisplayFare / per-pax Tax+TotalPrice.
        Stores AdminMarkup on PriceBreakup for persistence; strip before client responses.
        Returns markup amount applied.
        """
        params = self._markup_params_from_flight(flight)
        if params is None:
            return 0.0
        price = flight.get("Price")
        if not isinstance(price, dict):
            return 0.0
        # Avoid double-applying if the same Price dict is reused from cache.
        if (
            float(
                price.get("AdminMarkup")
                or (price.get("PriceBreakup") or {}).get("AdminMarkup")
                or 0
            )
            > 0
        ):
            pb0 = price.get("PriceBreakup") if isinstance(price.get("PriceBreakup"), dict) else {}
            return float(pb0.get("AdminMarkup") or price.get("AdminMarkup") or 0)

        amount = float(price.get("TotalDisplayFare") or 0)
        markup_data = await self._markup.get_markup_amount_for_flight(params, amount)
        markup_amount = max(0.0, float(markup_data.get("amount") or 0))
        if markup_amount <= 0:
            return 0.0

        pb = price.get("PriceBreakup")
        if not isinstance(pb, dict):
            pb = {"Tax": 0.0, "BasicFare": 0.0}
            price["PriceBreakup"] = pb

        pax_breakup = price.get("PassengerBreakup")
        if not isinstance(pax_breakup, dict) or not pax_breakup:
            pb["AdminMarkup"] = markup_amount
            pb["Tax"] = self._round_amount(float(pb.get("Tax") or 0) + markup_amount)
            price["TotalDisplayFare"] = self._round_amount(
                float(pb.get("BasicFare") or 0) + float(pb["Tax"])
            )
            return markup_amount

        # PassengerBreakup amounts are per-passenger (City Travel / FE contract).
        pax_cnt = 0
        for pax in pax_breakup.values():
            if isinstance(pax, dict):
                pax_cnt += int(pax.get("PassengerCount") or 0)
        if pax_cnt < 1:
            pax_cnt = 1
        per_pax_markup = self._round_amount(markup_amount / pax_cnt)

        for pax in pax_breakup.values():
            if not isinstance(pax, dict):
                continue
            pax["Tax"] = self._round_amount(float(pax.get("Tax") or 0) + per_pax_markup)
            pax["TotalPrice"] = self._round_amount(
                float(pax.get("BasePrice") or 0) + float(pax["Tax"])
            )

        pb["AdminMarkup"] = markup_amount
        pb["Tax"] = self._round_amount(float(pb.get("Tax") or 0) + markup_amount)
        price["TotalDisplayFare"] = self._round_amount(
            float(pb.get("BasicFare") or 0) + float(pb["Tax"])
        )
        return markup_amount

    async def _prepare_flight_for_client(self, flight: dict[str, Any]) -> dict[str, Any]:
        """Deep-copy Price, apply markup, strip AdminMarkup for B2C."""
        row = dict(flight)
        if isinstance(row.get("Price"), dict):
            row["Price"] = copy.deepcopy(row["Price"])
        await self.set_flight_markup(row)
        return BookingMoneyForClient.strip_admin_markup_from_flight_row(row)

    async def _prepare_flights_for_client(self, flights: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for flight in flights:
            if isinstance(flight, dict):
                out.append(await self._prepare_flight_for_client(flight))
        return out

    async def create_search_session(
        self, search_data: dict[str, Any], user_id: str | None = None
    ) -> FlightSearchRow:
        now = timeutils.datetime_now()
        row = FlightSearchRow(
            id=str(uuid.uuid4()),
            user_id=user_id,
            trip_type=str(search_data.get("trip_type") or "oneway"),
            cabin_class=str(search_data.get("cabin_class") or "Economy"),
            adult_count=int(search_data.get("adult_config") or 1),
            child_count=int(search_data.get("child_config") or 0),
            infant_count=int(search_data.get("infant_config") or 0),
            search_data=search_data,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_search_session(self, search_id: str) -> FlightSearchRow | None:
        return await self._session.get(FlightSearchRow, search_id)

    def _get_active_flight_booking_sources(self) -> list[dict[str, Any]]:
        registry = get_integration_registry()
        flight_sub = registry.active_sub_modules.get("FLIGHT")
        if flight_sub is None:
            return []
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()
        for key, api in list(registry.active_booking_apis.items()):
            if ":" in key:
                continue
            if api.sub_module_id != flight_sub.id:
                continue
            if api.code in seen:
                continue
            seen.add(api.code)
            sources.append(
                {
                    "code": api.code,
                    "name": api.name,
                    "configuration": api.runtime_configuration(),
                    "id": str(api.id),
                }
            )
        return sources

    def resolve_provider(
        self,
        code: str,
        config: dict[str, Any] | None = None,
        api_id: str | None = None,
    ) -> FlightProvider | None:
        if code.lower() == "citytravel":
            return CityTravelFlightProvider(
                config or {},
                api_id,
                session=self._session,
                http_client=self._http,
                multi_http=self._curl,
            )
        logger.debug("No flight provider registered for code=%s", code)
        return None

    def resolve_provider_by_source(self, source: str) -> FlightProvider | None:
        registry = get_integration_registry()
        api = registry.resolve_booking_api(
            source, sub_module="FLIGHT"
        ) or registry.resolve_booking_api(source)
        if api is None:
            return None
        return self.resolve_provider(source, api.runtime_configuration(), str(api.id))

    def resolve_provider_from_token(self, result_token: str) -> FlightProvider | None:
        decoded = FlightCommon.decode_result_token(result_token)
        if not decoded:
            return None
        return self.resolve_provider_by_source(str(decoded["booking_source"]))

    async def search(self, search_id: str) -> AsyncIterator[dict[str, Any]]:
        session = await self.get_search_session(search_id)
        if not session:
            yield {"status": False, "message": "Invalid search session"}
            return

        raw_search = session.search_data if isinstance(session.search_data, dict) else {}
        search_data = {
            **raw_search,
            "search_id": search_id,
        }

        sources = self._get_active_flight_booking_sources()
        if not sources:
            yield {"status": False, "message": "No active flight booking sources"}
            return

        handle_map: dict[str, Any] = {}
        provider_by_code: dict[str, FlightProvider] = {}
        search_by_code: dict[str, dict[str, Any]] = {}

        for source in sources:
            code = str(source["code"])
            provider = self.resolve_provider(code, source["configuration"], source["id"])
            if provider is None:
                continue
            credentials_ready = getattr(provider, "credentials_ready", None)
            if callable(credentials_ready) and not credentials_ready():
                logger.warning(
                    "Skipping flight source %s: credentials missing in Integrations booking API config",
                    code,
                )
                continue
            search_for_provider = {
                **search_data,
                "booking_api_id": source["id"],
                "booking_source_code": code,
            }
            handles = provider.get_search_request(search_for_provider)
            if not handles:
                continue
            provider_by_code[code] = provider
            search_by_code[code] = search_for_provider
            handle_map[code] = handles

        if not handle_map:
            yield {
                "status": True,
                "message": "Completed",
                "data": {"flights": [], "moreResults": False},
                "errors": None,
            }
            return

        raw_q: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
        out_q: asyncio.Queue[dict[str, Any] | object] = asyncio.Queue()

        async def _on_response(provider_code: str, raw: str) -> None:
            await raw_q.put((provider_code, raw))

        async def _run_http() -> None:
            try:
                await self._curl.stream_execute(handle_map, _on_response)
            except Exception:
                logger.exception("Flight search multi-HTTP failed search_id=%s", search_id)
            finally:
                await raw_q.put(None)

        async def _process_raw() -> None:
            try:
                while True:
                    item = await raw_q.get()
                    if item is None:
                        break
                    provider_code, raw = item
                    provider = provider_by_code.get(provider_code)
                    search_for_provider = search_by_code.get(provider_code) or search_data
                    if provider is None:
                        continue
                    formatted = await provider.format_search_response(raw, search_for_provider)
                    flights = formatted.get("data") if isinstance(formatted, dict) else None
                    if not isinstance(flights, list) or not flights:
                        continue
                    marked = await self._prepare_flights_for_client(flights)
                    await out_q.put(
                        {
                            "status": True,
                            "message": "Inprogress",
                            "data": {"flights": marked, "moreResults": True},
                            "errors": None,
                        }
                    )
            except Exception:
                logger.exception("Flight search format failed search_id=%s", search_id)
            finally:
                await out_q.put(_SEARCH_DONE)

        http_task = asyncio.create_task(_run_http())
        proc_task = asyncio.create_task(_process_raw())
        try:
            while True:
                chunk = await out_q.get()
                if chunk is _SEARCH_DONE:
                    break
                if isinstance(chunk, dict):
                    yield chunk
        finally:
            await asyncio.gather(http_task, proc_task, return_exceptions=True)

        yield {
            "status": True,
            "message": "Completed",
            "data": {"flights": [], "moreResults": False},
            "errors": None,
        }

    async def get_upsell(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider not available"}
        decoded = FlightCommon.decode_result_token(result_token)
        assert decoded is not None
        result = await provider.get_upsell(str(decoded["token"]))
        if result.get("status") and isinstance(result.get("data"), list):
            result = {
                **result,
                "data": await self._prepare_flights_for_client(result["data"]),
            }
        return result

    async def get_update_fare_quote(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider not available"}
        decoded = FlightCommon.decode_result_token(result_token)
        assert decoded is not None
        result = await provider.get_update_fare_quote(str(decoded["token"]))
        if result.get("status") and isinstance(result.get("data"), dict):
            marked = await self._prepare_flight_for_client(result["data"])
            result = {**result, "data": marked}
        return result

    async def get_extra_services(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider not available"}
        decoded = FlightCommon.decode_result_token(result_token)
        assert decoded is not None
        return await provider.get_extra_services(str(decoded["token"]))

    async def pre_book(self, request: dict[str, Any]) -> dict[str, Any]:
        """Pay-then-hold draft: provider cache + DB + gateway order (no AeroBook)."""
        token = str(request.get("ResultToken") or request.get("resultToken") or "").strip()
        passengers_raw = request.get("Passengers") or request.get("passengers") or []
        existing_ref = str(
            request.get("app_reference") or request.get("AppReference") or ""
        ).strip()

        pay_repo = SqlAlchemyPaymentGatewayTransactionRepository(self._session)
        pay_svc = PaymentGatewayService(repository=pay_repo, http_client=self._http)
        registry = get_integration_registry()
        pg_code = str(request.get("pg_code") or "").strip().lower()
        pg_model = registry.resolve_payment_gateway(pg_code) if pg_code else None
        if pg_model is None and registry.active_payment_gateways:
            pg_model = next(iter(registry.active_payment_gateways.values()))

        # Retry payment for an existing draft booking — do not recreate booking rows.
        if existing_ref:
            booking = (
                await self._session.execute(
                    select(FlightBookingDetailsRow).where(
                        FlightBookingDetailsRow.app_reference == existing_ref
                    )
                )
            ).scalar_one_or_none()
            if booking is None:
                return {
                    "status": False,
                    "message": "Booking not found for app_reference",
                    "data": [],
                }
            if booking.status not in {"BOOKING_STARTED", "PENDING_PAYMENT"}:
                return {
                    "status": False,
                    "message": f"Booking cannot accept payment (status={booking.status})",
                    "data": [],
                }

            attrs = booking.attributes if isinstance(booking.attributes, dict) else {}
            prebook_token = str(attrs.get("prebook_result_token") or "").strip()
            charge_quote = (
                attrs.get("pricing_quote") if isinstance(attrs.get("pricing_quote"), dict) else {}
            )
            payable = float(charge_quote.get("final_total_fare") or 0)

            if await pay_svc.get_payment_status(existing_ref):
                return {
                    "status": True,
                    "message": "Payment already completed",
                    "data": {
                        "ResultToken": prebook_token,
                        "app_reference": existing_ref,
                        "pg_code": pg_model.code if pg_model else None,
                        "payment_status": "accepted",
                        "paid": True,
                    },
                }

            if payable <= 0:
                return {
                    "status": False,
                    "message": "Invalid booking amount for payment retry",
                    "data": [],
                }

            lead_name = (booking.email or "Passenger").split("@")[0] or "Passenger"
            payment = await pay_svc.create_and_initiate_payment(
                app_reference=existing_ref,
                pg_code=pg_model.code if pg_model else None,
                currency=AdminCurrency.code(),
                booking_amount=payable,
                amount=payable,
                firstname=lead_name,
                email=str(booking.email or ""),
                phone=str(booking.phone or ""),
                productinfo="FLIGHT",
                flight_booking_details_id=booking.id,
            )
            if not payment.get("status"):
                await self._session.rollback()
                return {
                    "status": False,
                    "message": str(payment.get("message") or "Unable to create payment record"),
                    "data": [],
                }

            return {
                "status": True,
                "message": "Payment retry created",
                "data": {
                    "ResultToken": prebook_token,
                    "app_reference": existing_ref,
                    "transaction_id": payment.get("transaction_id"),
                    "payment_url": payment.get("payment_url"),
                    "pg_code": payment.get("pg_code"),
                    "pg_reference_id": payment.get("pg_reference_id"),
                    "payment": payment.get("payment"),
                    "retry": True,
                },
            }

        if not token or not isinstance(passengers_raw, list) or not passengers_raw:
            return {
                "status": False,
                "message": "ResultToken and Passengers are required",
                "data": [],
            }

        passengers = [p for p in passengers_raw if isinstance(p, dict)]
        if not passengers:
            return {
                "status": False,
                "message": "ResultToken and Passengers are required",
                "data": [],
            }

        title_err = FlightCommon.validate_passenger_titles_for_booking(passengers)
        if title_err:
            return {"status": False, "message": title_err, "data": []}
        name_err = FlightCommon.validate_passenger_names_for_booking(passengers)
        if name_err:
            return {"status": False, "message": name_err, "data": []}
        contact_err = FlightCommon.validate_lead_contact_for_booking(passengers)
        if contact_err:
            return {"status": False, "message": contact_err, "data": []}

        decoded = FlightCommon.decode_result_token(token)
        if not decoded:
            return {"status": False, "message": "Invalid ResultToken", "data": []}
        provider = self.resolve_provider_from_token(token)
        if not provider:
            return {"status": False, "message": "Provider not found", "data": []}

        quote = cache_get(str(decoded["token"]))
        quote = quote if isinstance(quote, dict) else {}
        search_data = quote.get("searchData") if isinstance(quote.get("searchData"), dict) else {}
        travel_start, travel_end = FlightCommon.journey_date_bounds_from_flight_details(
            quote.get("flightDetails"),
            fallback_departure=str(
                search_data.get("depature") or search_data.get("departure") or ""
            ),
        )
        dob_err = FlightCommon.validate_passenger_dobs_for_booking(passengers, travel_start)
        if dob_err:
            return {"status": False, "message": dob_err, "data": []}
        doc_err = FlightCommon.validate_passenger_documents_for_booking(
            passengers,
            documents_required=bool(quote.get("DocumentsRequired")),
            document_ex_required=bool(quote.get("DocumentExDateRequired")),
            middle_name_required=bool(quote.get("MiddleNameRequired")),
            travel_end_date=travel_end or travel_start,
        )
        if doc_err:
            return {"status": False, "message": doc_err, "data": []}

        app_reference = FlightCommon.generate_app_reference()
        selected_services = (
            request.get("SelectedServices") or request.get("selected_services") or []
        )
        selected_tariffs = request.get("SelectedTariffs") or request.get("selected_tariffs") or []
        if not isinstance(selected_services, list):
            selected_services = []
        if not isinstance(selected_tariffs, list):
            selected_tariffs = []

        get_pre = provider.get_pre_book_data
        try:
            result = await get_pre(
                str(decoded["token"]),
                app_reference,
                passengers,
                selected_services=selected_services,
                selected_tariffs=selected_tariffs,
            )
        except TypeError:
            result = await get_pre(str(decoded["token"]), app_reference, passengers)

        if not result.get("status") or not isinstance(result.get("data"), dict):
            return {
                "status": False,
                "message": result.get("message") or "PreBook failed",
                "data": [],
            }

        token_data = dict(result["data"])
        if isinstance(token_data.get("Price"), dict):
            token_data["Price"] = copy.deepcopy(token_data["Price"])
        await self.set_flight_markup(token_data)
        # Admin discount rules not wired yet.
        discount_data = {"amount": 0, "isPercentage": False, "value": 0, "type": None}
        token_data.setdefault("Price", {})
        if isinstance(token_data["Price"], dict):
            token_data["Price"]["discount"] = discount_data

        charge_quote = await FlightPreBookQuote.compute(
            self._session,
            token_data,
            discount_data,
            passengers,
            str(request.get("promo_code") or "").strip() or None,
            pg_model,
        )
        trim_promo = str(request.get("promo_code") or "").strip()
        if trim_promo and not charge_quote.get("promocode_applied"):
            return {
                "status": False,
                "message": charge_quote.get("promo_message") or "Promo code is not valid",
                "data": [],
            }
        if isinstance(token_data.get("Price"), dict):
            token_data["Price"]["total_seat_price"] = charge_quote["seat_selection_total"]
            token_data["Price"]["total_baggage_price"] = charge_quote["baggage_selection_total"]
            token_data["Price"]["total_meal_price"] = charge_quote["meal_selection_total"]
            token_data["Price"]["PromoDiscount"] = charge_quote["promo_discount"]
            token_data["Price"]["ConvenienceFee"] = charge_quote["convenience_fee_amount"]
            token_data["Price"]["PayableTotal"] = charge_quote["final_total_fare"]

        booking = await persist_pre_book(
            self._session,
            app_reference=app_reference,
            booking_source=str(decoded["booking_source"]),
            token_data=token_data,
            passengers=passengers,
            charge_quote=charge_quote,
            payment_gateway_code=pg_model.code if pg_model else None,
            fare_quote_token=token,
        )

        lead = passengers[0]
        lead_name = (
            f"{lead.get('FirstName') or lead.get('first_name') or ''} "
            f"{lead.get('LastName') or lead.get('last_name') or ''}"
        ).strip() or "Passenger"
        email = str(lead.get("Email") or lead.get("email") or "")
        phone = str(lead.get("ContactNo") or lead.get("phone") or "")

        payment = await pay_svc.create_and_initiate_payment(
            app_reference=app_reference,
            pg_code=pg_model.code if pg_model else None,
            currency=AdminCurrency.code(),
            booking_amount=charge_quote["final_total_fare"],
            amount=charge_quote["final_total_fare"],
            firstname=lead_name,
            email=email,
            phone=phone,
            productinfo="FLIGHT",
            flight_booking_details_id=booking.id,
        )
        if not payment.get("status"):
            await self._session.rollback()
            return {
                "status": False,
                "message": str(payment.get("message") or "Unable to create payment record"),
                "data": [],
            }

        token_data["transaction_id"] = payment.get("transaction_id")
        token_data["payment_url"] = payment.get("payment_url")
        token_data["app_reference"] = app_reference
        token_data["pg_code"] = payment.get("pg_code")
        token_data["pg_reference_id"] = payment.get("pg_reference_id")
        token_data["payment"] = payment.get("payment")
        token_data["payment_gateways"] = [
            {
                "code": g.code,
                "name": g.name,
                "convenience_type": g.convenience_type,
                "convenience_value": g.convenience_value,
            }
            for g in registry.active_payment_gateways.values()
        ]
        # Never expose AdminMarkup to B2C clients (keep it on persisted Price for txn).
        client_data = dict(token_data)
        if isinstance(client_data.get("Price"), dict):
            client_data["Price"] = copy.deepcopy(client_data["Price"])
        client_data = BookingMoneyForClient.strip_admin_markup_from_flight_row(client_data)
        return {"status": True, "data": client_data, "message": "Pre Booking data saved"}

    async def process_booking(self, request: dict[str, Any]) -> dict[str, Any]:
        """After payment: hold (AeroBook) → auto-issue (ConfirmBook) → persist snapshot."""
        result = await self.hold_ticket(request)
        if not result.get("status"):
            return result

        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        idempotent = bool(result.get("idempotent_replay"))
        confirmation_pending = bool(
            (data.get("Attr") or {}).get("confirmationPending")
            if isinstance(data.get("Attr"), dict)
            else data.get("confirmation_pending")
        )
        ticketing = data.get("ticketing") if isinstance(data.get("ticketing"), dict) else {}
        already_ticketed = bool(
            isinstance(ticketing.get("Passengers"), list) and ticketing.get("Passengers")
        )

        # City Travel happy path: hold then issue. Skip if already ticketed / deferred / pending.
        if not idempotent and not confirmation_pending and not already_ticketed:
            result = await self._maybe_auto_issue_after_hold(request, result)
            data = result.get("data") if isinstance(result.get("data"), dict) else {}
            confirmation_pending = bool(
                (data.get("Attr") or {}).get("confirmationPending")
                if isinstance(data.get("Attr"), dict)
                else False
            )

        if confirmation_pending:
            data["confirmation_pending"] = True
            data["status"] = data.get("status") or "BOOKING_CONFIRMATION_PENDING"
            result["message"] = result.get("message") or "Booking in progress"
        elif idempotent:
            data["status"] = data.get("status") or "BOOKING_CONFIRMED"
            result["message"] = result.get("message") or "Booking already confirmed"
        else:
            data["status"] = data.get("status") or "BOOKING_CONFIRMED"
            result["message"] = "Booking Successful"
        result["data"] = data
        return result

    async def hold_ticket(self, request: dict[str, Any]) -> dict[str, Any]:
        token = str(request.get("ResultToken") or request.get("resultToken") or "").strip()
        if not token:
            return {"status": False, "message": "ResultToken is required", "data": []}

        decoded = FlightCommon.decode_result_token(token)
        if not decoded:
            return {"status": False, "message": "Invalid ResultToken", "data": []}

        token_data = cache_get(str(decoded["token"]))
        token_data = token_data if isinstance(token_data, dict) else {}
        app_reference = str(token_data.get("app_reference") or "").strip()
        if not app_reference:
            return {
                "status": False,
                "message": "Pre-book session missing app_reference",
                "data": [],
            }

        pay_svc = PaymentGatewayService(
            repository=SqlAlchemyPaymentGatewayTransactionRepository(self._session),
            http_client=self._http,
        )
        if not await pay_svc.get_payment_status(app_reference):
            return {"status": False, "message": "Payment not completed", "data": []}

        existing = await self._find_existing_confirmed_hold(app_reference, decoded)
        if existing is not None:
            data = self._hold_response_from_booking(existing)
            if data:
                return {
                    "status": True,
                    "message": "Booking already confirmed",
                    "data": data,
                    "idempotent_replay": True,
                }

        provider = self.resolve_provider_from_token(token)
        if not provider:
            return {"status": False, "message": "Provider not found", "data": []}

        hold = await provider.hold_ticket({**request, "ResultToken": token})
        if hold.get("status") and isinstance(hold.get("data"), dict):
            hold["data"]["app_reference"] = hold["data"].get("app_reference") or app_reference
            await self._persist_booking_snapshot_after_hold(hold["data"])
            return hold

        await self._persist_booking_hold_failure(app_reference)
        return {
            "status": False,
            "message": hold.get("message") or "Hold failed",
            "data": [],
        }

    async def _maybe_auto_issue_after_hold(
        self, request: dict[str, Any], hold_response: dict[str, Any]
    ) -> dict[str, Any]:
        data = hold_response.get("data") if isinstance(hold_response.get("data"), dict) else {}
        booking_id = str(data.get("bookingId") or data.get("booking_id") or "").strip()
        if not booking_id:
            return hold_response

        token = str(request.get("ResultToken") or request.get("resultToken") or "").strip()
        provider = self.resolve_provider_from_token(token) if token else None
        if not provider:
            return hold_response

        issue = await provider.issue_ticket(booking_id)
        if not issue.get("status"):
            logger.warning(
                "Auto issue ticket failed app_reference=%s booking_id=%s message=%s",
                data.get("app_reference"),
                booking_id,
                issue.get("message"),
            )
            return hold_response

        issue_data = issue.get("data") if isinstance(issue.get("data"), dict) else {}
        attr = data.get("Attr") if isinstance(data.get("Attr"), dict) else {}
        if issue_data.get("confirmationPending"):
            data["Attr"] = {**attr, "confirmationPending": True}
            if issue_data.get("gdspnr"):
                data["gdspnr"] = issue_data["gdspnr"]
            hold_response["data"] = data
        else:
            data["ticketing"] = {**issue_data, "auto_issued": True}
            if issue_data.get("gdspnr"):
                data["gdspnr"] = issue_data["gdspnr"]
            hold_response["data"] = data

        await self._persist_booking_snapshot_after_hold(hold_response["data"])
        return hold_response

    async def _find_existing_confirmed_hold(
        self, app_reference: str, decoded: dict[str, Any]
    ) -> FlightBookingDetailsRow | None:
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return None
        if booking.status not in {
            "BOOKING_CONFIRMED",
            "BOOKING_CONFIRMATION_PENDING",
        }:
            return None
        expected_source = str(decoded.get("booking_source") or "").strip().lower()
        if expected_source and str(booking.booking_source or "").strip().lower() != expected_source:
            return None
        gdspnr = str(booking.gdspnr or "").strip()
        booking_id = str(booking.booking_id or "").strip()
        if booking.status == "BOOKING_CONFIRMED" and not gdspnr and not booking_id:
            return None
        if booking.status == "BOOKING_CONFIRMATION_PENDING" and not gdspnr and not booking_id:
            return None
        if not isinstance(booking.details_snapshot, dict) or not booking.details_snapshot:
            return None
        return booking

    @staticmethod
    def _hold_response_from_booking(booking: FlightBookingDetailsRow) -> dict[str, Any]:
        raw = booking.details_snapshot if isinstance(booking.details_snapshot, dict) else {}
        if not raw:
            return {}
        data = dict(raw)
        data["app_reference"] = booking.app_reference
        data["gdspnr"] = str(data.get("gdspnr") or booking.gdspnr or "")
        bid = str(booking.booking_id or "")
        if bid:
            data["booking_id"] = data.get("booking_id") or data.get("bookingId") or bid
            data["bookingId"] = data.get("bookingId") or data.get("booking_id") or bid
        data["status"] = booking.status
        return data

    async def _persist_booking_snapshot_after_hold(self, data: dict[str, Any]) -> None:
        app_ref = str(data.get("app_reference") or "").strip()
        if not app_ref:
            return
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return

        ticketing = data.get("ticketing") if isinstance(data.get("ticketing"), dict) else {}
        gdspnr = str(data.get("gdspnr") or data.get("GDSPNR") or "").strip()
        booking_id = str(data.get("bookingId") or data.get("booking_id") or "").strip()
        book_guid = str(data.get("book_guid") or data.get("BookGuid") or "").strip()
        if gdspnr:
            booking.gdspnr = gdspnr
        if booking_id:
            booking.booking_id = booking_id
        if book_guid:
            booking.book_guid = book_guid

        attr = data.get("Attr") if isinstance(data.get("Attr"), dict) else {}
        pending = bool(attr.get("confirmationPending")) or bool(
            ticketing.get("confirmationPending")
        )
        has_tickets = bool(
            isinstance(ticketing.get("Passengers"), list) and ticketing.get("Passengers")
        )
        supplier_status = str(data.get("BookingStatus") or "").strip().lower()
        if supplier_status in {"cancelled", "canceled"} or data.get("cancelled"):
            booking.status = "BOOKING_CANCELLED"
        elif pending and not has_tickets:
            booking.status = "BOOKING_CONFIRMATION_PENDING"
        elif has_tickets or gdspnr or booking_id:
            booking.status = "BOOKING_CONFIRMED"
        else:
            booking.status = "BOOKING_CONFIRMATION_PENDING"

        attrs = dict(booking.attributes or {}) if isinstance(booking.attributes, dict) else {}
        attrs["hold"] = {
            "booking_id": booking_id,
            "book_guid": book_guid,
            "gdspnr": gdspnr,
            "status": booking.status,
        }
        if pending:
            attrs["confirmation_pending"] = True
        booking.attributes = attrs
        booking.details_snapshot = data
        booking.updated_at = timeutils.datetime_now()
        await self._session.flush()

    async def _persist_booking_hold_failure(self, app_reference: str) -> None:
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return
        if booking.status in {"BOOKING_CONFIRMED", "BOOKING_CONFIRMATION_PENDING"}:
            return
        booking.status = "BOOKING_FAILED"
        booking.updated_at = timeutils.datetime_now()
        await self._session.flush()

    async def get_booking_details(self, app_reference: str) -> dict[str, Any]:
        app_ref = str(app_reference or "").strip()
        if not app_ref:
            return {"status": False, "message": "app_reference is required", "data": []}
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return {"status": False, "message": "Booking not found", "data": []}

        snapshot = (
            dict(booking.details_snapshot) if isinstance(booking.details_snapshot, dict) else {}
        )
        txn = (
            await self._session.execute(
                select(FlightBookingTransactionDetailsRow).where(
                    FlightBookingTransactionDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        pax_rows = list(
            (
                await self._session.execute(
                    select(FlightBookingPassengerDetailsRow).where(
                        FlightBookingPassengerDetailsRow.app_reference == app_ref
                    )
                )
            )
            .scalars()
            .all()
        )
        itinerary_rows = list(
            (
                await self._session.execute(
                    select(FlightBookingItineraryDetailsRow).where(
                        FlightBookingItineraryDetailsRow.app_reference == app_ref
                    )
                )
            )
            .scalars()
            .all()
        )

        data = {
            **snapshot,
            "app_reference": booking.app_reference,
            "status": booking.status,
            "booking_source": booking.booking_source,
            "booking_id": booking.booking_id,
            "book_guid": booking.book_guid,
            "gdspnr": booking.gdspnr,
            "trip_type": booking.trip_type,
            "cabin_class": booking.cabin_class,
            "origin": booking.origin,
            "destination": booking.destination,
            "departure_date": str(booking.departure_date or ""),
            "return_date": str(booking.return_date or ""),
            "email": booking.email,
            "phone": booking.phone,
            "passengers": [
                {
                    "title": p.title,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "age_type": p.age_type,
                    "date_of_birth": p.date_of_birth,
                    "nationality": p.nationality,
                    "document_number": p.document_number,
                }
                for p in pax_rows
            ],
            "itinerary": [
                {
                    "airline_code": i.airline_code,
                    "flight_number": i.flight_number,
                    "origin": i.origin,
                    "destination": i.destination,
                    "departure_datetime": i.departure_datetime,
                    "arrival_datetime": i.arrival_datetime,
                    "cabin_class": i.cabin_class,
                    "rph": i.rph,
                }
                for i in itinerary_rows
            ],
            "transaction": None
            if txn is None
            else {
                "basic_fare": float(txn.basic_fare or 0),
                # B2C: fold markup into tax; never expose admin_markup.
                "airline_tax": float(txn.airline_tax or 0) + float(txn.admin_markup or 0),
                "convenience_fee": float(txn.convenience_fee or 0),
                "total_fare": float(txn.total_fare or 0),
                "currency": txn.currency,
                "payment_mode": txn.payment_mode,
            },
        }
        data = BookingMoneyForClient.strip_admin_markup_from_flight_row(data)
        return {"status": True, "data": data, "message": "Success"}

    async def refresh_booking_status(self, app_reference: str) -> dict[str, Any]:
        app_ref = str(app_reference or "").strip()
        if not app_ref:
            return {"status": False, "message": "App reference is required", "data": []}
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return {"status": False, "message": "Booking not found", "data": []}
        booking_id = str(booking.booking_id or "").strip()
        if not booking_id:
            return {
                "status": False,
                "message": "Supplier booking reference is missing",
                "data": [],
            }

        provider = self.resolve_provider_by_source(str(booking.booking_source or ""))
        if not provider:
            return {"status": False, "message": "Provider not found", "data": []}

        refresh = await provider.refresh_booking_from_supplier(
            booking_id,
            {
                "app_reference": app_ref,
                "book_guid": booking.book_guid,
            },
        )
        if refresh.get("status") and isinstance(refresh.get("data"), dict):
            data = refresh["data"]
            data["app_reference"] = app_ref
            # Merge into existing snapshot
            snap = (
                dict(booking.details_snapshot) if isinstance(booking.details_snapshot, dict) else {}
            )
            merged = {**snap, **data}
            if isinstance(data.get("ticketing"), dict):
                merged["ticketing"] = data["ticketing"]
            await self._persist_booking_snapshot_after_hold(merged)
            return {
                "status": True,
                "message": refresh.get("message") or "Status updated",
                "data": {
                    "refresh_outcome": refresh.get("outcome"),
                    "app_reference": app_ref,
                    "status": booking.status,
                },
            }
        return {
            "status": False,
            "message": refresh.get("message") or "Refresh failed",
            "data": [],
        }

    async def cancel_booking(self, app_reference: str) -> dict[str, Any]:
        """Cancel / VOID via provider (City Travel: OrderInfo → AnnulateBook)."""
        app_ref = str(app_reference or "").strip()
        if not app_ref:
            return {"status": False, "message": "App reference is required", "data": []}

        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return {"status": False, "message": "Booking not found", "data": []}

        if booking.status == "BOOKING_CANCELLED":
            return {
                "status": True,
                "message": "Booking is already cancelled",
                "already_cancelled": True,
                "data": {"app_reference": app_ref, "status": booking.status},
            }

        if booking.status in {"BOOKING_STARTED", "BOOKING_FAILED"}:
            return {
                "status": False,
                "message": f"Cannot cancel booking in status {booking.status}",
                "data": {"app_reference": app_ref, "status": booking.status},
            }

        booking_id = str(booking.booking_id or "").strip()
        book_guid = str(booking.book_guid or "").strip()
        if not booking_id or not book_guid:
            return {
                "status": False,
                "message": "Supplier booking reference is missing (BookId/BookGuid)",
                "data": [],
            }

        provider = self.resolve_provider_by_source(str(booking.booking_source or ""))
        if not provider:
            return {"status": False, "message": "Provider not found", "data": []}

        cancel = await provider.cancel_booking(
            booking_id,
            {
                "app_reference": app_ref,
                "book_guid": book_guid,
            },
        )
        if not cancel.get("status"):
            return {
                "status": False,
                "message": cancel.get("message") or "Cancel failed",
                "data": cancel.get("data") or [],
            }

        await self._persist_booking_cancelled(
            app_ref,
            cancel.get("data") if isinstance(cancel.get("data"), dict) else {},
        )
        return {
            "status": True,
            "message": cancel.get("message") or "Booking cancelled",
            "already_cancelled": bool(cancel.get("already_cancelled")),
            "data": {
                "app_reference": app_ref,
                "status": "BOOKING_CANCELLED",
                "supplier": cancel.get("data") or {},
            },
        }

    async def _persist_booking_cancelled(
        self, app_reference: str, supplier_data: dict[str, Any]
    ) -> None:
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return
        booking.status = "BOOKING_CANCELLED"
        snap = dict(booking.details_snapshot) if isinstance(booking.details_snapshot, dict) else {}
        merged = {**snap, **supplier_data, "BookingStatus": "Cancelled", "cancelled": True}
        booking.details_snapshot = merged
        attrs = dict(booking.attributes or {}) if isinstance(booking.attributes, dict) else {}
        attrs["cancel"] = {
            "at": timeutils.datetime_now().isoformat(),
            "booking_id": str(supplier_data.get("bookingId") or booking.booking_id or ""),
            "book_guid": str(supplier_data.get("book_guid") or booking.book_guid or ""),
            "supplier_status": str(supplier_data.get("BookingStatus") or "Cancelled"),
        }
        booking.attributes = attrs
        booking.updated_at = timeutils.datetime_now()
        await self._session.flush()

    async def validate_flight_promo(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Validate promo against fare-quote token fare (base + taxes including markup).
        SSR (meal / baggage / seat) is excluded from the promo evaluation base.
        """
        token = str(request.get("ResultToken") or request.get("resultToken") or "").strip()
        promo_code = str(request.get("promo_code") or request.get("promoCode") or "").strip()
        if not token:
            return {"status": False, "message": "ResultToken is required", "data": []}
        if not promo_code:
            return {"status": False, "message": "Promo code is required", "data": []}

        provider = self.resolve_provider_from_token(token)
        if not provider:
            return {
                "status": False,
                "message": "Invalid token or provider not available",
                "data": [],
            }
        decoded = FlightCommon.decode_result_token(token)
        if decoded is None:
            return {"status": False, "message": "Invalid ResultToken", "data": []}

        result = await provider.get_flight_row_from_token_for_pricing(str(decoded["token"]))
        if not result.get("status") or not isinstance(result.get("data"), dict):
            return {
                "status": False,
                "message": result.get("message") or "Failed to load fare from token",
                "data": [],
            }

        row = dict(result["data"])
        if isinstance(row.get("Price"), dict):
            row["Price"] = copy.deepcopy(row["Price"])
        await self.set_flight_markup(row)
        price = row.get("Price") if isinstance(row.get("Price"), dict) else {}
        try:
            gross = float(price.get("TotalDisplayFare") or 0)
        except TypeError, ValueError:
            gross = 0.0
        # Admin discount rules not wired yet — promo base is fare + tax (incl. markup).
        admin_discount = 0.0
        promo_base = max(0.0, round(gross - admin_discount, 4))

        eval_result = await FlightPromo.evaluate(self._session, promo_code, promo_base)
        data = {
            **eval_result,
            "gross_display_fare_admin": round(gross, 4),
            "promo_evaluation_base_admin": round(promo_base, 4),
            "admin_discount_amount_admin": round(admin_discount, 4),
            "admin_currency": AdminCurrency.code(),
        }
        if not eval_result.get("applicable"):
            return {
                "status": False,
                "message": eval_result.get("message") or "Promo code is not applicable",
                "data": data,
            }
        return {
            "status": True,
            "message": eval_result.get("message") or "Applied successfully",
            "data": data,
        }

    async def not_implemented(self, action: str) -> dict[str, Any]:
        return {"status": False, "message": f"{action} is not implemented yet"}
