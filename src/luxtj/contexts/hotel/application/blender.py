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
from luxtj.contexts.hotel.application.markup import HotelMarkup
from luxtj.contexts.hotel.application.prebook_quote import HotelPreBookQuote
from luxtj.contexts.hotel.application.promo import HotelPromo
from luxtj.contexts.hotel.domain.common import HotelCommon
from luxtj.contexts.hotel.domain.provider import HotelProvider
from luxtj.contexts.hotel.infrastructure.block_cache import cache_get
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
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
            city_id=str(search_data.get("city_id") or ""),
            checkin_date=date.fromisoformat(str(checkin)[:10]),
            checkout_date=date.fromisoformat(str(checkout)[:10]),
            nationality=str(search_data.get("nationality") or search_data.get("Nationality") or "US")
            .upper()[:2],
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
        api = registry.resolve_booking_api(source, sub_module="HOTEL") or registry.resolve_booking_api(
            source
        )
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
            "city_id": session.city_id,
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
            "city_id": str(inner.get("city_id") or ""),
            "hotel_code": str(inner.get("hid") or ""),
            "check_in_date": str(inner.get("checkin") or ""),
        }
        result["data"] = await self._apply_markup_to_room_list(result["data"], base_params)
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
            "city_id": str(inner.get("city_id") or ""),
            "hotel_code": str(inner.get("hid") or ""),
            "star_rating": star if star > 0 else None,
            "check_in_date": str(inner.get("checkin") or ""),
        }
        basis = float(room.get("amount") or 0)
        mk = await self._markup.get_markup_amount_for_hotel(params, basis)
        if mk["amount"] > 0:
            room["taxes"] = round(float(room.get("taxes") or 0) + mk["amount"], 2)
            room["TotalTax"] = room["taxes"]
            room["amount"] = round(basis + mk["amount"], 2)
        room["_teenva_admin_markup"] = mk["amount"]
        return result

    async def validate_hotel_promo(self, request: dict[str, Any]) -> dict[str, Any]:
        list_token = str(request.get("ResultToken") or request.get("resultToken") or "").strip()
        promo_code = str(request.get("promo_code") or "").strip()
        if not list_token:
            return {"ok": False, "message": "ResultToken is required", "data": {}}
        decoded = HotelCommon.decode_list_token(list_token)
        if not decoded:
            return {"ok": False, "message": "Invalid ResultToken", "data": {}}
        inner = decoded.get("data") if isinstance(decoded.get("data"), dict) else {}
        snapshot = cache_get(HotelCommon.hotel_block_snapshot_cache_key(list_token))
        if not isinstance(snapshot, dict):
            return {
                "ok": False,
                "message": "Booking session expired. Please select your room again.",
                "data": {},
            }
        room = snapshot.get("room")
        if not isinstance(room, dict):
            return {"ok": False, "message": "Invalid cached booking data", "data": {}}
        if str(room.get("BookingCode") or "") != list_token:
            return {"ok": False, "message": "List token mismatch", "data": {}}
        b = HotelPreBookQuote.supplier_pricing_baseline(room, inner)
        payable = float(b["payable_after_supplier_discount"])
        currency = str(b["currency"])
        rate = float(AdminCurrency.rate_to_admin_or_one(currency))
        payable_admin = round(payable * rate, 2)
        eval_result = await HotelPromo.evaluate(self._session, promo_code, payable_admin)
        data = {
            **eval_result,
            "payable_after_supplier_discount": round(payable, 2),
            "gross_display_fare_admin": round(payable_admin, 2),
            "admin_currency": AdminCurrency.code(),
            "currency_conversion_rate": round(rate, 6),
            "supplier_currency": currency,
        }
        return {"ok": True, "data": data}

    async def pre_book(self, list_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_list_token(list_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider"}
        return await provider.pre_book(list_token)

    async def cancel_booking(self, app_reference: str) -> dict[str, Any]:
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == app_reference
                )
            )
        ).scalar_one_or_none()
        if not booking:
            return {"status": False, "message": "Booking not found"}
        provider = self.resolve_provider_by_source(booking.booking_source)
        if not provider:
            return {"status": False, "message": f"Provider not found for {booking.booking_source}"}
        result = await provider.cancel_booking(booking.booking_reference or "")
        if result.get("status"):
            booking.status = "CANCELLED"
            await self._session.flush()
        return result

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
                    "hotel_check_in": booking.hotel_check_in.isoformat(),
                    "hotel_check_out": booking.hotel_check_out.isoformat(),
                    "transaction": {
                        "total": float(txn.total) if txn else 0,
                        "currency": txn.currency if txn else AdminCurrency.code(),
                    }
                    if txn
                    else None,
                    "itineraries": [
                        {
                            "room_type_name": i.room_type_name,
                            "status": i.status,
                            "base_fare": float(i.base_fare),
                            "taxes": float(i.taxes),
                        }
                        for i in itineraries
                    ],
                    "passengers": [
                        {
                            "title": p.title,
                            "first_name": p.first_name,
                            "last_name": p.last_name,
                            "email": p.email,
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
                "city_id": str(search_data.get("city_id") or ""),
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
                    v["amount"] = round(basis + mk["amount"], 2)
                new_vars.append(v)
            room = dict(room)
            room["roomVariations"] = new_vars
            amounts = [float(x.get("amount") or 0) for x in new_vars if isinstance(x, dict)]
            room["TotalFare"] = round(min(amounts), 2) if amounts else float(room.get("TotalFare") or 0)
            out.append(room)
        return out
