"""B2C hotel dispatcher — mirrors TeenvaHotelController service/{requestType}."""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_models import (
    CityRow,
    CountryRow,
)
from luxtj.contexts.hotel.application.blender import HotelBlender
from luxtj.contexts.hotel.application.prebook_quote import HotelPreBookQuote
from luxtj.contexts.hotel.domain.common import HotelCommon
from luxtj.contexts.hotel.infrastructure.block_cache import cache_put
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
    ApiCityMapRow,
    HotelBookingCancellationQueueRow,
    HotelBookingDetailsRow,
    HotelBookingItineraryDetailsRow,
    HotelBookingPaxDetailsRow,
    HotelBookingTransactionDetailsRow,
)
from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import HotelCrsHotelRow
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.contexts.payment.application.service import PaymentGatewayService
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPaymentGatewayTransactionRepository,
)
from luxtj.shared_kernel.presentation.http.dependencies import (
    crs_database_session_handle,
    database_session_handle,
    http_client_handle,
)
from luxtj.utils import timeutils

hotel_router = APIRouter(prefix="/hotel", tags=["hotel"])


def _ok(data: Any = None, message: str = "Success", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        {"success": True, "message": message, "data": data if data is not None else []},
        status_code=status_code,
    )


def _err(
    message: str,
    errors: Any = None,
    data: Any = None,
    status_code: int = 400,
) -> JSONResponse:
    return JSONResponse(
        {
            "success": False,
            "message": message,
            "errors": errors or [],
            "data": data if data is not None else [],
        },
        status_code=status_code,
    )


def _blender(
    session: AsyncSession, crs_session: AsyncSession, http_client: Any
) -> HotelBlender:
    return HotelBlender(session, crs_session=crs_session, http_client=http_client)


@hotel_router.post("/service/{request_type}")
async def hotel_service(
    request_type: str,
    request: Request,
    session: AsyncSession = Depends(database_session_handle),
    crs_session: AsyncSession = Depends(crs_database_session_handle),
    http_client: Any = Depends(http_client_handle),
) -> Any:
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    blender = _blender(session, crs_session, http_client)
    handlers = {
        "GetCities": _get_cities,
        "PreSearch": _pre_search,
        "GetSearch": _get_search,
        "Search": _search,
        "Details": _details,
        "RoomList": _room_list,
        "BlockRoom": _block_room,
        "ValidateHotelPromo": _validate_promo,
        "PreBook": _pre_book,
        "ProcessBooking": _process_booking,
        "GetBookingDetails": _get_booking_details,
        "CancelBooking": _cancel_booking,
        "RequestCancellation": _request_cancellation,
    }
    handler = handlers.get(request_type)
    if handler is None:
        return _err("Invalid Service", status_code=400)
    return await handler(body, session, blender, request)


async def _get_cities(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    search = str(body.get("search") or "").strip()
    if len(search) < 2:
        return _err("Search term must be at least 2 characters")
    pattern = f"%{search}%"
    registry = get_integration_registry()
    hotel_sub = registry.active_sub_modules.get("HOTEL")
    active_api_ids = [
        str(api.id)
        for api in registry.active_booking_apis.values()
        if ":" not in str(api.code)
        and hotel_sub is not None
        and api.sub_module_id == hotel_sub.id
    ]
    active_api_ids = list({i for i in active_api_ids})

    from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
        BookingSourceRegionMapRow,
        NewCitiesNRegionRow,
    )

    crs = blender._crs_session
    # Prefer Path B catalogue regions mapped for active booking APIs.
    region_stmt = (
        select(NewCitiesNRegionRow)
        .join(
            BookingSourceRegionMapRow,
            BookingSourceRegionMapRow.new_cities_n_region_id == NewCitiesNRegionRow.id,
        )
        .where(NewCitiesNRegionRow.name.ilike(pattern))
    )
    if active_api_ids:
        region_stmt = region_stmt.where(
            BookingSourceRegionMapRow.booking_source_id.in_(active_api_ids)
        )
    region_stmt = region_stmt.order_by(NewCitiesNRegionRow.name).distinct()
    regions = list((await crs.execute(region_stmt)).scalars().all())
    if regions:
        data = [
            {
                "city_name": r.name,
                "country_name": r.country_name,
                "country_code": r.country_code,
                "city_id": r.id,
                "region_type": r.type,
            }
            for r in regions
        ]
        return _ok(data, "Cities found")

    # Legacy fallback: geo cities via api_city_map
    stmt = (
        select(CityRow, CountryRow)
        .join(CountryRow, CountryRow.id == CityRow.country_id)
        .join(ApiCityMapRow, ApiCityMapRow.city_fk == CityRow.id)
        .where(CityRow.name.ilike(pattern))
        .where(CityRow.status.is_(True))
    )
    if active_api_ids:
        stmt = stmt.where(ApiCityMapRow.api_fk.in_(active_api_ids))
    stmt = stmt.order_by(CityRow.name).distinct()
    rows = (await session.execute(stmt)).all()
    data = [
        {
            "city_name": city.name,
            "country_name": country.name,
            "country_code": country.code,
            "city_id": city.id,
        }
        for city, country in rows
    ]
    return _ok(data, "Cities found")


async def _pre_search(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    city_id = body.get("city") or body.get("city_id")
    checkin = body.get("checkinDate") or body.get("checkin_date")
    checkout = body.get("checkoutDate") or body.get("checkout_date")
    rooms_raw = body.get("rooms") or []
    if not isinstance(rooms_raw, list):
        rooms_raw = []
    for i, room in enumerate(rooms_raw):
        if not isinstance(room, dict):
            continue
        cc = int(room.get("childCount") or room.get("child_count") or 0)
        ages = room.get("childAges") or room.get("child_ages")
        if cc > 0 and (not isinstance(ages, list) or len(ages) != cc):
            return _err(
                "Child age is required",
                {"rooms": f"Room {i + 1}: child ages are required (0–17) for each child."},
            )
    rooms = HotelCommon.normalize_rooms_for_search(rooms_raw)
    nationality = str(body.get("nationality") or "US").upper()
    currency = str(body.get("currency") or AdminCurrency.code() or "USD").upper()
    if not city_id:
        return _err("City is required", {"city": "City is required"})
    if not checkin:
        return _err("Check-in date is required", {"checkinDate": "Required"})
    if not checkout:
        return _err("Check-out date is required", {"checkoutDate": "Required"})
    if not rooms:
        return _err("At least one room is required", {"rooms": "Required"})
    search_data = {
        "city_id": str(city_id),
        "checkin_date": checkin,
        "checkout_date": checkout,
        "rooms": rooms,
        "nationality": nationality,
        "currency": currency,
    }
    row = await blender.create_search_session(search_data)
    return _ok({"search_id": row.id}, "Search session created")


async def _get_search(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    search_id = str(body.get("search_id") or "")
    row = await blender.get_search_session(search_id)
    if not row:
        return _err("Search session not found", status_code=404)
    search_data = dict(row.search_data) if isinstance(row.search_data, dict) else {}
    search_data.pop("residency", None)
    search_data.pop("Residency", None)
    if not search_data.get("city_name"):
        from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
            NewCitiesNRegionRow,
        )

        region = await blender._crs_session.get(NewCitiesNRegionRow, row.city_id)
        if region:
            search_data["city_name"] = region.name
            search_data["country_name"] = region.country_name
            search_data["country_code"] = region.country_code
        else:
            city = await session.get(CityRow, row.city_id)
            if city:
                search_data["city_name"] = city.name
                country = await session.get(CountryRow, city.country_id)
                search_data["country_name"] = country.name if country else ""
    return _ok({"search_data": search_data}, "Success")


async def _search(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> StreamingResponse:
    search_id = str(body.get("search_id") or "")

    async def generate():
        async for chunk in blender.search(search_id):
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _details(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    token = str(body.get("ResultToken") or "")
    if not token:
        return _err("ResultToken is required")
    result = await blender.get_hotel_details(token)
    return (
        _ok(result.get("data") or [], "Success")
        if result.get("status")
        else _err(result.get("message") or "Error")
    )


async def _room_list(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    token = str(body.get("ListToken") or body.get("ResultToken") or "")
    if not token:
        return _err("ListToken is required")
    result = await blender.get_room_list(token)
    return (
        _ok({"rooms": result.get("data") or []}, "Success")
        if result.get("status")
        else _err(result.get("message") or "Error")
    )


async def _block_room(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    token = str(body.get("ResultToken") or "")
    if not token:
        return _err("ResultToken is required")
    result = await blender.block_room(token, [])
    if not result.get("status"):
        return _err(result.get("message") or "BlockRoom failed")
    data = result.get("data") or {}
    registry = get_integration_registry()
    data["payment_gateways"] = [
        {
            "code": g.code,
            "name": g.name,
            "convenience_type": g.convenience_type,
            "convenience_value": g.convenience_value,
        }
        for g in registry.active_payment_gateways.values()
    ]
    list_token = str((data.get("room") or {}).get("BookingCode") or "")
    if list_token:
        cache_put(HotelCommon.hotel_block_snapshot_cache_key(list_token), data, 45 * 60)
    if isinstance(data.get("room"), dict):
        data["room"] = dict(data["room"])
        data["room"].pop("_teenva_admin_markup", None)
    return _ok(data, "Room blocked successfully")


async def _validate_promo(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    result = await blender.validate_hotel_promo(body)
    if not result.get("ok"):
        return _err(result.get("message") or "Failed", data=result.get("data") or [], status_code=422)
    data = result.get("data") or {}
    if not data.get("applicable"):
        return _err(data.get("message") or "Promo code is not applicable", data=data, status_code=422)
    return _ok(data, data.get("message") or "Applied successfully")


async def _pre_book(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    from luxtj.contexts.hotel.infrastructure.block_cache import cache_get

    list_token = str(body.get("resultToken") or body.get("ListToken") or "")
    pax_details = body.get("pax-details") or body.get("pax_details") or []
    email = str(body.get("email") or "")
    phone = str(body.get("phone_no") or body.get("phone") or "")
    pg_code = str(body.get("pg_code") or "")
    promo_code = str(body.get("promo_code") or "").strip()
    if not list_token:
        return _err("resultToken is required")
    if not pax_details:
        return _err("Passenger details are required")
    if not email:
        return _err("Email is required")
    decoded = HotelCommon.decode_list_token(list_token)
    if not decoded:
        return _err("Invalid resultToken")
    inner = decoded.get("data") or {}
    booking_source = str(decoded.get("booking_source") or "ratehawk")
    snapshot = cache_get(HotelCommon.hotel_block_snapshot_cache_key(list_token))
    if not isinstance(snapshot, dict):
        return _err("Booking session expired. Please select your room again.")
    room = snapshot.get("room")
    hotel_snap = snapshot.get("Hotel") if isinstance(snapshot.get("Hotel"), dict) else {}
    if not isinstance(room, dict):
        return _err("Invalid cached booking data")
    if str(room.get("BookingCode") or "") != list_token:
        return _err("List token mismatch")

    registry = get_integration_registry()
    pg_model = registry.resolve_payment_gateway(pg_code.lower()) if pg_code else None
    if pg_model is None and registry.active_payment_gateways:
        pg_model = next(iter(registry.active_payment_gateways.values()))

    quote = await HotelPreBookQuote.compute(
        session, room, inner, promo_code or None, 0.0, pg_model
    )
    room_count, guest_adults, guest_children = HotelPreBookQuote.count_guests(room)
    fx = float(quote.get("currency_conversion_rate") or 1)
    crs_hotel_code = str(
        inner.get("hotel_crs_hotel_code") or inner.get("hotel_crs_hotel_id") or ""
    )
    if not crs_hotel_code:
        return _err("Hotel session is invalid. Please select your room again.")
    crs_hotel = (
        await blender._crs_session.execute(
            select(HotelCrsHotelRow).where(HotelCrsHotelRow.code == crs_hotel_code)
        )
    ).scalar_one_or_none()
    if crs_hotel is None:
        # Backward-compat: older tokens stored CRS UUID in hotel_crs_hotel_id
        crs_hotel = await blender._crs_session.get(HotelCrsHotelRow, crs_hotel_code)
    if crs_hotel is None:
        return _err("Hotel not found in inventory.")
    crs_hotel_code = str(crs_hotel.code)
    hotel_crs_room_code = str(inner.get("hotel_crs_room_code") or "") or None

    # Idempotent PreBook: reuse open PENDING_PAYMENT booking for same list_token.
    existing_rows = (
        await session.execute(
            select(HotelBookingDetailsRow).where(
                HotelBookingDetailsRow.status == "PENDING_PAYMENT",
                HotelBookingDetailsRow.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    for row in existing_rows:
        attrs = row.attributes if isinstance(row.attributes, dict) else {}
        if str(attrs.get("list_token") or "") != list_token:
            continue
        pay_repo = SqlAlchemyPaymentGatewayTransactionRepository(session)
        pay_svc = PaymentGatewayService(
            repository=pay_repo,
            http_client=blender._http,
        )
        txns = await pay_repo.list_by_app_reference(row.app_reference)
        pending = next((t for t in txns if t.status == "pending"), None)
        pay_token = HotelCommon.encode_result_token(
            row.booking_source,
            json.dumps({"app_reference": row.app_reference, "list_token": list_token}),
        )
        return _ok(
            {
                "ResultToken": pay_token,
                "app_reference": row.app_reference,
                "transaction_id": pending.transaction_id if pending else row.app_reference,
                "payment_url": (
                    pay_svc.payment_url_for(pending.transaction_id)
                    if pending
                    else pay_svc.payment_url_for(row.app_reference)
                ),
                "idempotent": True,
            },
            "Pre Booking data already saved",
        )

    app_ref = HotelCommon.generate_app_reference()
    lead = pax_details[0] if isinstance(pax_details[0], dict) else {}
    now = timeutils.datetime_now()
    conv_type = (
        "percentage"
        if quote["convenience_type"] == "percentage"
        else ("plus" if quote["convenience_type"] == "flat" else None)
    )
    session.add(
        HotelBookingDetailsRow(
            id=str(uuid.uuid4()),
            hotel_crs_hotel_code=crs_hotel_code,
            app_reference=app_ref,
            booking_source=booking_source,
            status="PENDING_PAYMENT",
            hotel_name="",
            star_rating=0,
            hotel_code=str(inner.get("hid") or ""),
            hotel_check_in=date.fromisoformat(str(inner.get("checkin") or now.date())[:10]),
            hotel_check_out=date.fromisoformat(str(inner.get("checkout") or now.date())[:10]),
            rooms=room_count,
            total_adults=guest_adults,
            total_children=guest_children,
            attributes={
                "list_token": list_token,
                "pricing_quote": quote,
                "promo_code": quote.get("promo_code_applied"),
            },
            created_at=now,
            updated_at=now,
        )
    )
    itinerary_id = str(uuid.uuid4())
    session.add(
        HotelBookingItineraryDetailsRow(
            id=itinerary_id,
            app_reference=app_ref,
            hotel_crs_room_code=hotel_crs_room_code,
            room_type_name=str(room.get("Name") or ""),
            status="PENDING_PAYMENT",
            base_fare=round(float(room.get("BaseFare") or 0) * fx, 2),
            taxes=round(float(room.get("TotalTax") or room.get("taxes") or 0) * fx, 2),
            adults=guest_adults,
            children=guest_children,
            attributes={
                "meal_code": str(room.get("meal_code") or ""),
                "meal_display": str(room.get("meal") or ""),
                "breakfast_included": bool(room.get("breakfastIncluded") or False),
                "child_meal_included": bool(room.get("childMealIncluded") or False),
                "free_cancellation_before": room.get("freeCancellationBefore"),
                "variation": str(room.get("variation") or ""),
            },
            created_at=now,
            updated_at=now,
        )
    )
    await HotelCommon.persist_itinerary_cancellation_policies_and_extra_fees(
        session, app_ref, itinerary_id, room, fx, str(quote["currency"])[:3]
    )
    session.add(
        HotelBookingTransactionDetailsRow(
            id=str(uuid.uuid4()),
            app_reference=app_ref,
            base_fare=quote["room_rate_exclusive_supplier"],
            taxes=quote["taxes_supplier"],
            admin_markup=quote["admin_markup"],
            convenience_value=quote["convenience_value_raw"],
            convenience_value_type=conv_type,
            convenience_amount=quote["convenience_fee"],
            promo_code=quote.get("promo_code_applied"),
            discount=quote["supplier_discount"],
            admin_discount=quote["promo_discount"],
            admin_discount_value=quote.get("promo_rule_amount"),
            admin_discount_type=quote.get("promo_discount_type"),
            total=quote["total_charge"],
            currency=str(quote["currency"])[:3],
            conversion_rate=fx,
            payment_mode=pg_model.code.lower() if pg_model else None,
            created_at=now,
            updated_at=now,
        )
    )
    for pax in pax_details:
        if not isinstance(pax, dict):
            continue
        session.add(
            HotelBookingPaxDetailsRow(
                id=str(uuid.uuid4()),
                app_reference=app_ref,
                title=str(pax.get("salutation") or pax.get("title") or "") or None,
                first_name=str(pax.get("first_name") or ""),
                last_name=str(pax.get("last_name") or ""),
                phone_code=str(pax.get("country_code") or "") or None,
                phone=phone or None,
                email=email or None,
                pax_type="Adult",
                created_at=now,
                updated_at=now,
            )
        )
    await session.flush()

    pay_svc = PaymentGatewayService(
        repository=SqlAlchemyPaymentGatewayTransactionRepository(session),
        http_client=blender._http,
    )
    lead_name = (
        f"{lead.get('first_name') or ''} {lead.get('last_name') or ''}".strip() or "Guest"
    )
    payment = await pay_svc.create_payment_record(
        app_reference=app_ref,
        pg_code=pg_model.code if pg_model else None,
        currency=str(quote["currency"]),
        booking_amount=quote["total_charge"],
        amount=quote["total_charge"],
        firstname=lead_name,
        email=email,
        phone=phone or "",
        productinfo=str(hotel_snap.get("name") or hotel_snap.get("HotelName") or "HOTEL"),
    )
    if not payment.get("status"):
        await session.rollback()
        return _err(str(payment.get("message") or "Unable to create payment record"))

    pay_token = HotelCommon.encode_result_token(
        booking_source,
        json.dumps({"app_reference": app_ref, "list_token": list_token}),
    )
    room_client = dict(room)
    room_client.pop("_teenva_admin_markup", None)
    return _ok(
        {
            "ResultToken": pay_token,
            "app_reference": app_ref,
            "transaction_id": payment.get("transaction_id"),
            "payment_url": payment.get("payment_url"),
            "Hotel": hotel_snap,
            "room": room_client,
            "Price": {
                "Currency": quote["currency"],
                "TotalDisplayFare": quote["total_charge"],
                "PayableBeforeConvenience": quote["payable_before_convenience"],
                "ConvenienceFee": quote["convenience_fee"],
                "SupplierDiscount": quote["supplier_discount"],
                "PromoDiscount": quote["promo_discount"],
                "Taxes": quote["taxes_supplier"],
                "RoomRateExclusive": quote["room_rate_exclusive_supplier"],
            },
            "payment_gateways": [
                {"code": g.code, "name": g.name}
                for g in registry.active_payment_gateways.values()
            ],
        },
        "Pre Booking data Saved",
    )


async def _process_booking(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    result_token = str(body.get("ResultToken") or "")
    if not result_token:
        return _err("ResultToken is required")
    decoded = HotelCommon.decode_result_token(result_token)
    if not decoded:
        return _err("Invalid ResultToken")
    try:
        inner = json.loads(decoded.get("token") or "{}")
    except Exception:
        inner = {}
    app_ref = str(inner.get("app_reference") or "")
    list_token = str(inner.get("list_token") or "")
    booking_source = str(decoded.get("booking_source") or "ratehawk")
    if not app_ref:
        return _err("Invalid token data")
    booking = (
        await session.execute(
            select(HotelBookingDetailsRow).where(HotelBookingDetailsRow.app_reference == app_ref)
        )
    ).scalar_one_or_none()
    if not booking:
        return _err("Booking not found", status_code=404)
    if booking.status == "BOOKING_CONFIRMED":
        return _ok({"app_reference": app_ref, "status": "BOOKING_CONFIRMED"}, "Booking already confirmed")
    if booking.status == "BOOKING_AWAITING_CONFIRMATION":
        return _ok(
            {
                "app_reference": app_ref,
                "status": "BOOKING_AWAITING_CONFIRMATION",
                "pending_supplier_confirmation": True,
            },
            "Awaiting supplier confirmation",
        )
    if not list_token:
        attrs = booking.attributes if isinstance(booking.attributes, dict) else {}
        list_token = str(attrs.get("list_token") or "")
    if not list_token:
        return _err("List token not found – cannot confirm with supplier")

    pay_svc = PaymentGatewayService(
        repository=SqlAlchemyPaymentGatewayTransactionRepository(session),
        http_client=blender._http,
    )
    if not await pay_svc.get_payment_status(app_ref):
        return _err(
            "Payment not completed",
            data={"app_reference": app_ref, "payment_required": True},
            status_code=402,
        )

    pax_rows = list(
        (
            await session.execute(
                select(HotelBookingPaxDetailsRow).where(
                    HotelBookingPaxDetailsRow.app_reference == app_ref
                )
            )
        )
        .scalars()
        .all()
    )
    passengers = [
        {"Title": p.title, "FirstName": p.first_name, "LastName": p.last_name} for p in pax_rows
    ]
    provider = blender.resolve_provider_by_source(booking_source)
    if not provider:
        return _err("Hotel provider not found")
    result = await provider.process_booking(
        {
            "ListToken": list_token,
            "Passengers": passengers,
            "AppReference": app_ref,
            "user_ip": request.client.host if request.client else "127.0.0.1",
        }
    )
    if not result.get("status"):
        return _err(result.get("message") or "Supplier booking failed")
    data = result.get("data") or {}
    pending = bool(result.get("pending_supplier_confirmation"))
    if pending:
        attrs = dict(booking.attributes or {})
        if isinstance(data.get("RawResponse"), dict):
            attrs["ratehawk_pending_snapshot"] = data["RawResponse"]
        booking.booking_reference = str(data.get("BookingRef") or "")
        booking.status = "BOOKING_AWAITING_CONFIRMATION"
        booking.attributes = attrs
        await session.flush()
        return _ok(
            {
                "app_reference": app_ref,
                "booking_ref": data.get("BookingRef") or "",
                "status": "BOOKING_AWAITING_CONFIRMATION",
                "pending_supplier_confirmation": True,
            },
            "Awaiting supplier confirmation",
        )
    booking.booking_reference = str(data.get("BookingRef") or "")
    conf = str(data.get("ConfirmationReference") or "").strip()
    booking.confirmation_reference = conf or None
    booking.status = "BOOKING_CONFIRMED"
    await session.flush()
    return _ok(
        {
            "app_reference": app_ref,
            "booking_ref": data.get("BookingRef") or "",
            "confirmation_reference": conf,
            "status": "BOOKING_CONFIRMED",
        },
        "Booking Success",
    )


async def _get_booking_details(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    app_ref = str(body.get("app_reference") or body.get("AppReference") or "")
    if not app_ref:
        return _err("app_reference is required")
    result = await blender.get_booking_details(app_ref)
    return (
        _ok(result.get("data") or {}, "Booking details retrieved successfully")
        if result.get("status")
        else _err(result.get("message") or "Booking not found", status_code=404)
    )


async def _cancel_booking(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    app_ref = str(body.get("AppReference") or body.get("app_reference") or "")
    if not app_ref:
        return _err("AppReference is required")
    result = await blender.cancel_booking(app_ref)
    return (
        _ok(result.get("data") or [], "Booking cancelled")
        if result.get("status")
        else _err(result.get("message") or "Cancellation failed")
    )


async def _request_cancellation(
    body: dict[str, Any], session: AsyncSession, blender: HotelBlender, request: Request
) -> JSONResponse:
    app_ref = str(body.get("app_reference") or body.get("AppReference") or "")
    remark = str(body.get("remark") or body.get("Remark") or "")
    if not app_ref:
        return _err("app_reference is required")
    booking = (
        await session.execute(
            select(HotelBookingDetailsRow).where(HotelBookingDetailsRow.app_reference == app_ref)
        )
    ).scalar_one_or_none()
    if not booking:
        return _err("Booking not found", status_code=404)
    existing = (
        await session.execute(
            select(HotelBookingCancellationQueueRow).where(
                HotelBookingCancellationQueueRow.app_reference == app_ref,
                HotelBookingCancellationQueueRow.request_status.in_(["PENDING", "APPROVED"]),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return _err("Cancellation request already exists for this booking")
    now = timeutils.datetime_now()
    session.add(
        HotelBookingCancellationQueueRow(
            id=str(uuid.uuid4()),
            app_reference=app_ref,
            remark=remark,
            request_datetime=now,
            request_status="PENDING",
            created_at=now,
            updated_at=now,
        )
    )
    booking.status = "CANCELLATION_IN_PROCESS"
    await session.flush()
    return _ok(
        {"app_reference": app_ref, "status": "CANCELLATION_IN_PROCESS"},
        "Cancellation request submitted",
    )
