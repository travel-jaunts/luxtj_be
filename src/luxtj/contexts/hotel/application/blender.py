"""Hotel blender — mirrors TeenvaHotelBlender."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.currency.domain.booking_money_for_client import BookingMoneyForClient
from luxtj.contexts.hotel.application.markup import HotelMarkup
from luxtj.contexts.hotel.application.prebook_quote import HotelPreBookQuote
from luxtj.contexts.hotel.application.promo import HotelPromo
from luxtj.contexts.hotel.domain.common import HotelCommon
from luxtj.contexts.hotel.domain.provider import HotelProvider
from luxtj.contexts.hotel.infrastructure.block_cache import cache_get
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
    HotelBookingCancellationQueueRow,
    HotelBookingDetailsRow,
    HotelBookingItineraryDetailsRow,
    HotelBookingPaxDetailsRow,
    HotelBookingTransactionDetailsRow,
    HotelSearchRow,
)
from luxtj.contexts.hotel.infrastructure.ratehawk.provider import RateHawkHotelProvider
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.infrastructure.http import MultiHttpClient
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)

_SEARCH_DONE = object()


class HotelBlender:
    def __init__(
        self,
        session: AsyncSession,
        *,
        crs_session: AsyncSession | None = None,
        http_client: Any | None = None,
        multi_http: MultiHttpClient | None = None,
        hotel_markup: HotelMarkup | None = None,
    ) -> None:
        self._session = session
        self._crs_session = crs_session or session
        self._http = http_client
        self._curl = multi_http or MultiHttpClient(http_client, session=session)
        self._markup = hotel_markup or HotelMarkup(session, crs_session=self._crs_session)

    async def create_search_session(
        self, search_data: dict[str, Any], user_id: str | None = None
    ) -> HotelSearchRow:
        search_data = dict(search_data)
        search_data.pop("residency", None)
        search_data.pop("Residency", None)
        now = timeutils.datetime_now()
        checkin = search_data.get("checkin_date") or search_data.get("CheckIn") or ""
        checkout = search_data.get("checkout_date") or search_data.get("CheckOut") or ""
        row = HotelSearchRow(
            id=str(uuid.uuid4()),
            user_id=user_id,
            checkin_date=date.fromisoformat(str(checkin)[:10]),
            checkout_date=date.fromisoformat(str(checkout)[:10]),
            nationality=str(
                search_data.get("nationality") or search_data.get("Nationality") or "US"
            ).upper()[:2],
            search_data=search_data,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_search_session(self, search_id: str) -> HotelSearchRow | None:
        return await self._session.get(HotelSearchRow, search_id)

    def _get_active_hotel_booking_sources(self) -> list[dict[str, Any]]:
        registry = get_integration_registry()
        hotel_sub = registry.active_sub_modules.get("HOTEL")
        if hotel_sub is None:
            return []
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()
        for key, api in list(registry.active_booking_apis.items()):
            if ":" in key:
                continue
            if api.sub_module_id != hotel_sub.id:
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
        self, code: str, config: dict[str, Any] | None = None, api_id: str | None = None
    ) -> HotelProvider | None:
        if code.lower() == "ratehawk":
            return RateHawkHotelProvider(
                config or {},
                api_id,
                session=self._session,
                crs_session=self._crs_session,
                http_client=self._http,
            )
        return None

    def resolve_provider_by_source(self, source: str) -> HotelProvider | None:
        registry = get_integration_registry()
        api = registry.resolve_booking_api(
            source, sub_module="HOTEL"
        ) or registry.resolve_booking_api(source)
        if api is None:
            return None
        return self.resolve_provider(source, api.runtime_configuration(), str(api.id))

    def resolve_provider_from_token(self, result_token: str) -> HotelProvider | None:
        decoded = HotelCommon.decode_result_token(result_token)
        if not decoded:
            return None
        return self.resolve_provider_by_source(str(decoded["booking_source"]))

    def resolve_provider_from_list_token(self, list_token: str) -> HotelProvider | None:
        decoded = HotelCommon.decode_list_token(list_token)
        if not decoded:
            return None
        return self.resolve_provider_by_source(str(decoded["booking_source"]))

    async def search(self, search_id: str) -> AsyncIterator[dict[str, Any]]:
        session = await self.get_search_session(search_id)
        if not session:
            yield {"status": False, "message": "Invalid search session"}
            return

        raw_search = session.search_data if isinstance(session.search_data, dict) else {}
        admin_code = AdminCurrency.code()
        search_data = {
            **raw_search,
            "search_id": search_id,
            "checkin_date": session.checkin_date.isoformat(),
            "checkout_date": session.checkout_date.isoformat(),
            "currency": str(raw_search.get("currency") or admin_code).upper() or admin_code,
        }

        sources = self._get_active_hotel_booking_sources()
        if not sources:
            yield {"status": False, "message": "No active hotel booking sources"}
            return

        handle_map: dict[str, Any] = {}
        provider_by_code: dict[str, HotelProvider] = {}
        search_by_code: dict[str, dict[str, Any]] = {}

        for source in sources:
            code = str(source["code"])
            provider = self.resolve_provider(code, source["configuration"], source["id"])
            if provider is None:
                continue
            if isinstance(provider, RateHawkHotelProvider) and not provider.credentials_ready():
                logger.warning(
                    "Skipping RateHawk: credentials missing in Integrations booking API config"
                )
                continue

            search_for_provider = {
                **search_data,
                "booking_api_id": source["id"],
                "booking_source_code": code,
            }
            if isinstance(provider, RateHawkHotelProvider):
                handles = await provider.prepare_search_request(search_for_provider)
            else:
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
                "data": {"hotels": [], "moreResults": False},
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
                logger.exception("Hotel search multi-HTTP failed search_id=%s", search_id)
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

                    batches: list[list[dict[str, Any]]] = []
                    iter_batches = getattr(provider, "iter_search_hotel_batches", None)
                    if callable(iter_batches):
                        async for batch in iter_batches(raw, search_for_provider):
                            if isinstance(batch, list) and batch:
                                batches.append(batch)
                    else:
                        formatted = await provider.format_search_response(raw, search_for_provider)
                        data = formatted.get("data") if isinstance(formatted, dict) else None
                        if isinstance(data, list) and data:
                            batches.append(data)

                    for batch in batches:
                        marked = await self._apply_markup_to_search_hotels(
                            batch,
                            search_data,
                            provider_code.lower(),
                        )
                        await out_q.put(
                            {
                                "status": True,
                                "message": "Inprogress",
                                "data": {"hotels": marked, "moreResults": True},
                                "errors": None,
                            }
                        )
            except Exception:
                logger.exception("Hotel search format/enrich failed search_id=%s", search_id)
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
            "data": {"hotels": [], "moreResults": False},
            "errors": None,
        }

    async def get_hotel_details(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider"}
        return await provider.get_hotel_details(result_token)

    async def get_room_list(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider"}
        result = await provider.get_room_list(result_token)
        if not result.get("status") or not isinstance(result.get("data"), list):
            return result
        decoded = HotelCommon.decode_result_token(result_token)
        if decoded is None:
            return result
        try:
            inner = json.loads(decoded.get("token") or "{}")
        except Exception:
            inner = {}
        base_params = {
            "supplier_code": str(decoded.get("booking_source") or "ratehawk"),
            "region_id": str(inner.get("region_id") or ""),
            "country_code": str(inner.get("country_code") or ""),
            "hotel_code": str(inner.get("hid") or ""),
            "check_in_date": str(inner.get("checkin") or ""),
        }
        marked = await self._apply_markup_to_room_list(result["data"], base_params)
        result["data"] = BookingMoneyForClient.strip_admin_markup_from_hotel_rooms(marked)
        return result

    async def block_room(
        self, result_token: str, passengers: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider"}
        result = await provider.block_room(result_token, passengers or [])
        if not result.get("status") or not isinstance(result.get("data"), dict):
            return result
        decoded = HotelCommon.decode_result_token(result_token)
        if decoded is None:
            return result
        try:
            inner = json.loads(decoded.get("token") or "{}")
        except Exception:
            inner = {}
        room = result["data"].get("room")
        if not isinstance(room, dict):
            return result
        star = int(room.get("hotelStarRating") or 0)
        params = {
            "supplier_code": str(decoded.get("booking_source") or "ratehawk"),
            "region_id": str(inner.get("region_id") or ""),
            "country_code": str(inner.get("country_code") or ""),
            "hotel_code": str(inner.get("hid") or ""),
            "star_rating": star if star > 0 else None,
            "check_in_date": str(inner.get("checkin") or ""),
        }
        # Snapshot supplier tax before folding markup into client-facing taxes.
        supplier_taxes = round(float(room.get("TotalTax") or room.get("taxes") or 0), 2)
        basis = float(room.get("amount") or 0)
        mk = await self._markup.get_markup_amount_for_hotel(params, basis)
        if mk["amount"] > 0:
            room["taxes"] = round(supplier_taxes + mk["amount"], 2)
            room["TotalTax"] = room["taxes"]
            room["amount"] = round(basis + mk["amount"], 2)
            room["TotalFare"] = room["amount"]
        room["_teenva_supplier_taxes"] = supplier_taxes
        room["_teenva_admin_markup"] = mk["amount"]
        return result

    async def validate_hotel_promo(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Validate promo against BlockRoom list token fare.
        Promo base = base fare + taxes including markup (admin currency).
        """
        list_token = str(
            request.get("ResultToken")
            or request.get("resultToken")
            or request.get("ListToken")
            or ""
        ).strip()
        promo_code = str(request.get("promo_code") or request.get("promoCode") or "").strip()
        if not list_token:
            return {"status": False, "message": "ResultToken is required", "data": {}}
        if not promo_code:
            return {"status": False, "message": "Promo code is required", "data": {}}
        decoded = HotelCommon.decode_list_token(list_token)
        if not decoded:
            return {"status": False, "message": "Invalid ResultToken", "data": {}}
        inner = decoded.get("data") if isinstance(decoded.get("data"), dict) else {}
        snapshot = cache_get(HotelCommon.hotel_block_snapshot_cache_key(list_token))
        if not isinstance(snapshot, dict):
            return {
                "status": False,
                "message": "Booking session expired. Please select your room again.",
                "data": {},
            }
        room = snapshot.get("room")
        if not isinstance(room, dict):
            return {"status": False, "message": "Invalid cached booking data", "data": {}}
        if str(room.get("BookingCode") or "") != list_token:
            return {"status": False, "message": "List token mismatch", "data": {}}

        b = HotelPreBookQuote.supplier_pricing_baseline(room, inner)
        promo_base = max(
            0.0,
            float(b["room_rate_exclusive_supplier"]) + float(b["taxes_incl_markup"]),
        )
        currency = str(b["currency"])
        rate = float(AdminCurrency.rate_to_admin_or_one(currency))
        if rate <= 0:
            rate = 1.0
        promo_base_admin = round(promo_base * rate, 2)
        eval_result = await HotelPromo.evaluate(self._session, promo_code, promo_base_admin)
        discount_admin = float(eval_result.get("discount_amount_admin") or 0)
        # Booking/supplier currency amount for B2C UI (stay fare is not always admin).
        discount_booking = round(discount_admin / rate, 2) if rate > 0 else round(discount_admin, 2)
        discount_booking = min(discount_booking, round(promo_base, 2))
        data = {
            **eval_result,
            "discount_amount_admin": round(discount_admin, 2),
            "discount_amount": discount_booking,
            "gross_display_fare_admin": promo_base_admin,
            "promo_evaluation_base_admin": promo_base_admin,
            "promo_evaluation_base": round(promo_base, 2),
            "admin_currency": AdminCurrency.code(),
            "currency_conversion_rate": round(rate, 6),
            "supplier_currency": currency,
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

    async def pre_book(self, list_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_list_token(list_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider"}
        return await provider.pre_book(list_token)

    async def cancel_booking(self, app_reference: str) -> dict[str, Any]:
        """Cancel via supplier when a booking reference exists; otherwise local cancel."""
        app_ref = str(app_reference or "").strip()
        if not app_ref:
            return {"status": False, "message": "App reference is required", "data": []}

        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return {"status": False, "message": "Booking not found", "data": []}

        status = str(booking.status or "").upper()
        if status in {"CANCELLED", "BOOKING_CANCELLED"}:
            return {
                "status": True,
                "message": "Booking is already cancelled",
                "already_cancelled": True,
                "data": {"app_reference": app_ref, "status": "CANCELLED"},
            }

        if status in {"PENDING_PAYMENT", "BOOKING_FAILED"}:
            return {
                "status": False,
                "message": f"Cannot cancel booking in status {booking.status}",
                "data": {"app_reference": app_ref, "status": booking.status},
            }

        cancellable = {
            "BOOKING_CONFIRMED",
            "BOOKING_AWAITING_CONFIRMATION",
            "CANCELLATION_IN_PROCESS",
        }
        if status not in cancellable:
            return {
                "status": False,
                "message": f"Cannot cancel booking in status {booking.status}",
                "data": {"app_reference": app_ref, "status": booking.status},
            }

        booking_ref = str(booking.booking_reference or "").strip()
        supplier_payload: dict[str, Any] = {}
        if booking_ref:
            provider = self.resolve_provider_by_source(str(booking.booking_source or ""))
            if not provider:
                return {
                    "status": False,
                    "message": f"Provider not found for {booking.booking_source}",
                    "data": [],
                }
            cancel = await provider.cancel_booking(booking_ref)
            if not cancel.get("status"):
                return {
                    "status": False,
                    "message": cancel.get("message") or "Cancel failed",
                    "data": cancel.get("data") or [],
                }
            if isinstance(cancel.get("data"), dict):
                supplier_payload = cancel["data"]
            elif cancel.get("data") is not None:
                supplier_payload = {"supplier": cancel.get("data")}
        else:
            # No supplier order id yet (e.g. awaiting) — local cancel for ops/refunds.
            supplier_payload = {"local_only": True}

        await self._persist_hotel_cancelled(app_ref, supplier_payload)
        return {
            "status": True,
            "message": "Booking cancelled",
            "already_cancelled": False,
            "data": {
                "app_reference": app_ref,
                "status": "CANCELLED",
                "supplier": supplier_payload,
            },
        }

    async def _persist_hotel_cancelled(
        self, app_reference: str, supplier_data: dict[str, Any]
    ) -> None:
        now = timeutils.datetime_now()
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return
        booking.status = "CANCELLED"
        attrs = dict(booking.attributes or {}) if isinstance(booking.attributes, dict) else {}
        attrs["cancel"] = {
            "at": now.isoformat(),
            "booking_reference": str(booking.booking_reference or ""),
            "supplier": supplier_data,
        }
        booking.attributes = attrs
        booking.updated_at = now

        itineraries = list(
            (
                await self._session.execute(
                    select(HotelBookingItineraryDetailsRow).where(
                        HotelBookingItineraryDetailsRow.app_reference == app_reference
                    )
                )
            )
            .scalars()
            .all()
        )
        for it in itineraries:
            it.status = "CANCELLED"
            it.updated_at = now

        queue_rows = list(
            (
                await self._session.execute(
                    select(HotelBookingCancellationQueueRow).where(
                        HotelBookingCancellationQueueRow.app_reference == app_reference,
                        HotelBookingCancellationQueueRow.request_status.in_(
                            ["PENDING", "APPROVED"]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in queue_rows:
            row.request_status = "COMPLETED"
            row.admin_update_time = now
            row.updated_at = now
            if not row.admin_remark:
                row.admin_remark = "Cancelled via admin CancelBooking"

        await self._session.flush()

    async def persist_booking_failed(
        self, app_reference: str, *, message: str | None = None, supplier: Any = None
    ) -> None:
        """Mark paid-but-unconfirmed hotel booking as failed (supplier error after pay)."""
        app_ref = str(app_reference or "").strip()
        if not app_ref:
            return
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return
        status = str(booking.status or "").upper()
        if status in {
            "BOOKING_CONFIRMED",
            "BOOKING_AWAITING_CONFIRMATION",
            "CANCELLED",
            "BOOKING_CANCELLED",
        }:
            return
        now = timeutils.datetime_now()
        booking.status = "BOOKING_FAILED"
        booking.updated_at = now
        attrs = dict(booking.attributes or {}) if isinstance(booking.attributes, dict) else {}
        attrs["process_booking_failure"] = {
            "at": now.isoformat(),
            "message": str(message or "Supplier booking failed"),
            "supplier": supplier
            if isinstance(supplier, (dict, list, str, int, float, bool))
            else None,
        }
        booking.attributes = attrs

        itineraries = list(
            (
                await self._session.execute(
                    select(HotelBookingItineraryDetailsRow).where(
                        HotelBookingItineraryDetailsRow.app_reference == app_ref
                    )
                )
            )
            .scalars()
            .all()
        )
        for it in itineraries:
            if str(it.status or "").upper() not in {"CANCELLED", "BOOKING_CONFIRMED"}:
                it.status = "BOOKING_FAILED"
                it.updated_at = now
        await self._session.flush()

    async def refresh_booking_status(self, app_reference: str) -> dict[str, Any]:
        """Poll supplier (RateHawk finish/status + order/info) and update local status."""
        app_ref = str(app_reference or "").strip()
        if not app_ref:
            return {"status": False, "message": "App reference is required", "data": []}

        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return {"status": False, "message": "Booking not found", "data": []}

        status = str(booking.status or "").upper()
        if status in {"CANCELLED", "BOOKING_CANCELLED"}:
            return {
                "status": True,
                "message": "Booking is already cancelled",
                "outcome": "unchanged",
                "data": {"app_reference": app_ref, "status": booking.status},
            }

        attrs = dict(booking.attributes or {}) if isinstance(booking.attributes, dict) else {}
        partner_order_id = str(attrs.get("ratehawk_partner_order_id") or "").strip()
        order_id = attrs.get("ratehawk_order_id")
        booking_ref = str(booking.booking_reference or "").strip()
        if not partner_order_id and booking_ref:
            # ProcessBooking stores partner or numeric order id in booking_reference.
            partner_order_id = booking_ref

        if not partner_order_id and (order_id is None or order_id == ""):
            if status == "BOOKING_FAILED":
                return {
                    "status": True,
                    "message": "Booking is already failed",
                    "outcome": "unchanged",
                    "data": {"app_reference": app_ref, "status": "BOOKING_FAILED"},
                }
            fail_msg = "Supplier booking reference is missing"
            await self._persist_hotel_refresh(
                app_ref,
                {
                    "Status": "BOOKING_FAILED",
                    "BookingRef": booking_ref,
                    "ConfirmationReference": "",
                    "RawResponse": {"finish_status_error": fail_msg},
                    "message": fail_msg,
                },
                outcome="failed",
            )
            return {
                "status": True,
                "message": fail_msg,
                "outcome": "failed",
                "data": {
                    "app_reference": app_ref,
                    "status": "BOOKING_FAILED",
                    "confirmation_reference": "",
                    "booking_reference": booking_ref,
                },
            }

        provider = self.resolve_provider_by_source(str(booking.booking_source or ""))
        if not provider:
            return {
                "status": False,
                "message": f"Provider not found for {booking.booking_source}",
                "data": [],
            }

        refresh = await provider.refresh_booking_from_supplier(
            booking_ref or partner_order_id,
            {
                "app_reference": app_ref,
                "partner_order_id": partner_order_id,
                "order_id": order_id,
                "current_status": status,
                "finish_pending": bool(attrs.get("ratehawk_finish_pending")),
            },
        )
        if refresh.get("outcome") == "missing_ref" or (
            not refresh.get("status")
            and "reference is missing" in str(refresh.get("message") or "").lower()
        ):
            fail_msg = str(refresh.get("message") or "Supplier booking reference is missing")
            if status != "BOOKING_FAILED":
                await self._persist_hotel_refresh(
                    app_ref,
                    {
                        "Status": "BOOKING_FAILED",
                        "BookingRef": booking_ref,
                        "ConfirmationReference": "",
                        "RawResponse": {"finish_status_error": fail_msg},
                        "message": fail_msg,
                    },
                    outcome="failed",
                )
            return {
                "status": True,
                "message": fail_msg,
                "outcome": "failed",
                "data": {
                    "app_reference": app_ref,
                    "status": "BOOKING_FAILED",
                    "confirmation_reference": "",
                    "booking_reference": booking_ref,
                },
            }
        if not refresh.get("status"):
            return {
                "status": False,
                "message": refresh.get("message") or "Refresh failed",
                "data": refresh.get("data") or [],
            }

        data = refresh.get("data") if isinstance(refresh.get("data"), dict) else {}
        new_status = str(data.get("Status") or status).upper()
        outcome = str(refresh.get("outcome") or "unchanged")
        await self._persist_hotel_refresh(app_ref, data, outcome=outcome)
        return {
            "status": True,
            "message": refresh.get("message") or "Status updated",
            "outcome": outcome,
            "data": {
                "app_reference": app_ref,
                "status": new_status,
                "confirmation_reference": data.get("ConfirmationReference") or "",
                "booking_reference": data.get("BookingRef") or booking_ref,
            },
        }

    async def _persist_hotel_refresh(
        self, app_reference: str, data: dict[str, Any], *, outcome: str
    ) -> None:
        now = timeutils.datetime_now()
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return

        new_status = str(data.get("Status") or booking.status or "").upper()
        booking_ref = str(data.get("BookingRef") or "").strip()
        conf = str(data.get("ConfirmationReference") or "").strip()
        raw = data.get("RawResponse") if isinstance(data.get("RawResponse"), dict) else {}

        if booking_ref:
            booking.booking_reference = booking_ref
        if conf:
            booking.confirmation_reference = conf

        attrs = dict(booking.attributes or {}) if isinstance(booking.attributes, dict) else {}
        if raw.get("finish_status") is not None:
            attrs["ratehawk_finish_status"] = raw.get("finish_status")
        if raw.get("order_info") is not None:
            attrs["ratehawk_order_info"] = raw.get("order_info")
        if raw.get("finish_status_error"):
            attrs["ratehawk_finish_status_error"] = raw.get("finish_status_error")
        if outcome in {"confirmed", "failed", "cancelled"}:
            attrs.pop("ratehawk_awaiting_poll_attempts", None)
            attrs.pop("ratehawk_finish_pending", None)
        booking.attributes = attrs

        if outcome == "confirmed" or new_status == "BOOKING_CONFIRMED":
            booking.status = "BOOKING_CONFIRMED"
            itinerary_status = "BOOKING_CONFIRMED"
        elif outcome == "failed" or new_status == "BOOKING_FAILED":
            booking.status = "BOOKING_FAILED"
            itinerary_status = "BOOKING_FAILED"
            if raw.get("finish_status_error") or data.get("message"):
                attrs["process_booking_failure"] = {
                    "at": now.isoformat(),
                    "message": str(
                        raw.get("finish_status_error")
                        or data.get("message")
                        or "Supplier booking failed"
                    ),
                    "source": "refresh_status",
                }
                booking.attributes = attrs
        elif outcome == "cancelled" or new_status in {"CANCELLED", "BOOKING_CANCELLED"}:
            booking.status = "CANCELLED"
            itinerary_status = "CANCELLED"
        elif outcome == "awaiting":
            booking.status = "BOOKING_AWAITING_CONFIRMATION"
            itinerary_status = "BOOKING_AWAITING_CONFIRMATION"
        else:
            # unchanged — keep booking.status; still persist refs/attrs above
            itinerary_status = None

        booking.updated_at = now

        if itinerary_status:
            itineraries = list(
                (
                    await self._session.execute(
                        select(HotelBookingItineraryDetailsRow).where(
                            HotelBookingItineraryDetailsRow.app_reference == app_reference
                        )
                    )
                )
                .scalars()
                .all()
            )
            for it in itineraries:
                cur = str(it.status or "").upper()
                if cur in {"CANCELLED", "BOOKING_CANCELLED"} and itinerary_status != "CANCELLED":
                    continue
                it.status = itinerary_status
                it.updated_at = now

        await self._session.flush()

    async def get_booking_details(self, app_reference: str) -> dict[str, Any]:
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if not booking:
            return {"status": False, "message": "Booking not found"}
        txn = (
            await self._session.execute(
                select(HotelBookingTransactionDetailsRow).where(
                    HotelBookingTransactionDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        itineraries = list(
            (
                await self._session.execute(
                    select(HotelBookingItineraryDetailsRow).where(
                        HotelBookingItineraryDetailsRow.app_reference == app_reference
                    )
                )
            )
            .scalars()
            .all()
        )
        pax = list(
            (
                await self._session.execute(
                    select(HotelBookingPaxDetailsRow).where(
                        HotelBookingPaxDetailsRow.app_reference == app_reference
                    )
                )
            )
            .scalars()
            .all()
        )
        return {
            "status": True,
            "data": {
                "BookingDetails": {
                    "app_reference": booking.app_reference,
                    "status": booking.status,
                    "booking_source": booking.booking_source,
                    "booking_reference": booking.booking_reference,
                    "confirmation_reference": booking.confirmation_reference,
                    "hotel_name": booking.hotel_name,
                    "hotel_address": booking.hotel_address,
                    "hotel_location": booking.hotel_location,
                    "hotel_image": booking.hotel_image,
                    "star_rating": booking.star_rating,
                    "hotel_check_in": booking.hotel_check_in.isoformat(),
                    "hotel_check_out": booking.hotel_check_out.isoformat(),
                    "check_in_time": booking.check_in_time,
                    "check_out_time": booking.check_out_time,
                    "rooms": booking.rooms,
                    "total_adults": booking.total_adults,
                    "total_children": booking.total_children,
                    "email": (pax[0].email if pax else None),
                    "phone": (
                        f"{pax[0].phone_code or ''}{pax[0].phone or ''}".strip() if pax else None
                    ),
                    "transaction": (
                        None
                        if txn is None
                        else {
                            "base_fare": float(txn.base_fare),
                            # B2C: fold markup into taxes; never expose admin_markup.
                            "taxes": float(txn.taxes or 0) + float(txn.admin_markup or 0),
                            "convenience_amount": float(txn.convenience_amount or 0),
                            "admin_discount": float(txn.admin_discount or 0),
                            "discount": float(txn.discount or 0),
                            "total": float(txn.total or 0),
                            "total_fare": float(txn.total or 0),
                            "currency": txn.currency,
                            "payment_mode": txn.payment_mode,
                        }
                    ),
                    "itineraries": [
                        {
                            "room_type_name": i.room_type_name,
                            "status": i.status,
                            "base_fare": float(i.base_fare),
                            "taxes": float(i.taxes or 0)
                            + (
                                float(txn.admin_markup or 0)
                                if txn is not None and idx == 0
                                else 0.0
                            ),
                            "adults": i.adults,
                            "children": i.children,
                        }
                        for idx, i in enumerate(itineraries)
                    ],
                    "passengers": [
                        {
                            "title": p.title,
                            "first_name": p.first_name,
                            "last_name": p.last_name,
                            "email": p.email,
                            "phone": p.phone,
                            "phone_code": p.phone_code,
                            "pax_type": p.pax_type,
                        }
                        for p in pax
                    ],
                }
            },
        }

    async def _apply_markup_to_search_hotels(
        self, hotels: list[Any], search_data: dict[str, Any], supplier_code: str
    ) -> list[Any]:
        nights = HotelCommon.hotel_stay_nights(
            str(search_data.get("checkin_date") or ""),
            str(search_data.get("checkout_date") or ""),
        )
        out: list[Any] = []
        for hotel in hotels:
            if not isinstance(hotel, dict):
                out.append(hotel)
                continue
            basis = float(hotel.get("price") or 0)
            params = {
                "supplier_code": supplier_code,
                "region_id": str(search_data.get("region_id") or hotel.get("region_id") or ""),
                "country_code": str(search_data.get("country_code") or ""),
                "hotel_code": str(hotel.get("HotelCode") or ""),
                "star_rating": int(hotel.get("star") or 0) or None,
                "check_in_date": str(search_data.get("checkin_date") or ""),
            }
            if params["star_rating"] is not None and params["star_rating"] <= 0:
                params["star_rating"] = None
            mk = await self._markup.get_markup_amount_for_hotel(params, basis)
            if mk["amount"] > 0:
                hotel = dict(hotel)
                hotel["price"] = round(basis + mk["amount"], 2)
                hotel["price_per_night"] = (
                    round(hotel["price"] / nights, 2) if nights > 0 else hotel["price"]
                )
            out.append(hotel)
        return out

    async def _apply_markup_to_room_list(
        self, rooms: list[Any], base_params: dict[str, Any]
    ) -> list[Any]:
        out: list[Any] = []
        for room in rooms:
            if not isinstance(room, dict):
                out.append(room)
                continue
            star = int(room.get("hotelStarRating") or 0)
            params = {**base_params, "star_rating": star if star > 0 else None}
            variations = room.get("roomVariations")
            if not isinstance(variations, list):
                out.append(room)
                continue
            new_vars: list[Any] = []
            for v in variations:
                if not isinstance(v, dict):
                    new_vars.append(v)
                    continue
                v = dict(v)
                basis = float(v.get("amount") or 0)
                mk = await self._markup.get_markup_amount_for_hotel(params, basis)
                if mk["amount"] > 0:
                    v["taxes"] = round(float(v.get("taxes") or 0) + mk["amount"], 2)
                    v["TotalTax"] = v["taxes"]
                    v["amount"] = round(basis + mk["amount"], 2)
                    v["TotalFare"] = v["amount"]
                v["_teenva_admin_markup"] = mk["amount"]
                new_vars.append(v)
            room = dict(room)
            room["roomVariations"] = new_vars
            amounts = [float(x.get("amount") or 0) for x in new_vars if isinstance(x, dict)]
            room["TotalFare"] = (
                round(min(amounts), 2) if amounts else float(room.get("TotalFare") or 0)
            )
            out.append(room)
        return out
