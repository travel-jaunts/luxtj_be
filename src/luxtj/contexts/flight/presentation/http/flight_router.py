"""B2C flight dispatcher — POST /flight/service/{request_type}."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.flight.application.blender import FlightBlender
from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
)

flight_router = APIRouter(prefix="/flight", tags=["flight"])


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


def _blender(session: AsyncSession, http_client: Any) -> FlightBlender:
    return FlightBlender(session, http_client=http_client)


@flight_router.post("/service/{request_type}")
async def flight_service(
    request_type: str,
    request: Request,
    session: AsyncSession = Depends(database_session_handle),
    http_client: Any = Depends(http_client_handle),
) -> Any:
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    blender = _blender(session, http_client)
    handlers = {
        "PreSearch": _pre_search,
        "GetSearch": _get_search,
        "Search": _search,
        "UpSell": _upsell,
        "UpdateFareQuote": _update_fare_quote,
        "ValidateFlightPromo": _validate_promo,
        "ExtraServices": _extra_services,
        "PreBook": _pre_book,
        "ProcessBooking": _process_booking,
        "GetBookingDetails": _get_booking_details,
        "RefreshBookingStatus": _refresh_booking_status,
        "CancelBooking": _cancel_booking,
    }
    handler = handlers.get(request_type)
    if handler is None:
        return _err("Invalid Service", status_code=400)
    return await handler(body, session, blender, request)


async def _pre_search(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    clean, err = FlightCommon.normalize_search_request(body)
    if err or clean is None:
        return _err(err or "Invalid search request")
    row = await blender.create_search_session(clean)
    return _ok({"search_id": row.id, "search_data": clean}, "Search session created")


async def _get_search(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    search_id = str(body.get("search_id") or "")
    row = await blender.get_search_session(search_id)
    if not row:
        return _err("Search session not found", status_code=404)
    search_data = dict(row.search_data) if isinstance(row.search_data, dict) else {}
    return _ok({"search_data": search_data, "search_id": row.id}, "Success")


async def _search(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> StreamingResponse:
    search_id = str(body.get("search_id") or "")

    async def generate():
        async for chunk in blender.search(search_id):
            # Normalize stream shape toward FE contract.
            if chunk.get("status") is False:
                yield (
                    json.dumps(
                        {
                            "success": False,
                            "message": chunk.get("message") or "Error",
                            "data": chunk.get("data") or {"flights": [], "moreResults": False},
                        }
                    )
                    + "\n"
                )
                continue
            yield (
                json.dumps(
                    {
                        "success": True,
                        "message": chunk.get("message") or "Success",
                        "data": chunk.get("data") or {"flights": [], "moreResults": False},
                    }
                )
                + "\n"
            )

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _upsell(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    token = str(body.get("ResultToken") or body.get("resultToken") or "")
    if not token:
        return _err("ResultToken is required")
    result = await blender.get_upsell(token)
    return (
        _ok(result.get("data") or [], result.get("message") or "Success")
        if result.get("status")
        else _err(result.get("message") or "UpSell failed")
    )


async def _update_fare_quote(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    token = str(body.get("ResultToken") or body.get("resultToken") or "")
    if not token:
        return _err("ResultToken is required")
    result = await blender.get_update_fare_quote(token)
    if not result.get("status"):
        return _err(result.get("message") or "UpdateFareQuote failed")
    data = result.get("data") or {}
    if isinstance(data, dict):
        registry = get_integration_registry()
        data = dict(data)
        data["payment_gateways"] = [
            {
                "code": g.code,
                "name": g.name,
                "convenience_type": g.convenience_type,
                "convenience_value": g.convenience_value,
            }
            for g in registry.active_payment_gateways.values()
        ]
    return _ok(data, result.get("message") or "Success")


async def _extra_services(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    token = str(body.get("ResultToken") or body.get("resultToken") or "")
    if not token:
        return _err("ResultToken is required")
    result = await blender.get_extra_services(token)
    return (
        _ok(result.get("data") or [], result.get("message") or "Success")
        if result.get("status")
        else _err(result.get("message") or "ExtraServices failed")
    )


async def _validate_promo(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    result = await blender.validate_flight_promo(body if isinstance(body, dict) else {})
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status"):
        return _ok(data, result.get("message") or "Applied successfully")
    return _err(
        result.get("message") or "Promo code is not valid",
        data=data or None,
        status_code=422,
    )


async def _pre_book(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    result = await blender.pre_book(body if isinstance(body, dict) else {})
    if not result.get("status"):
        return _err(result.get("message") or "PreBook failed")
    return _ok(result.get("data") or {}, result.get("message") or "Success")


async def _process_booking(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    result = await blender.process_booking(body if isinstance(body, dict) else {})
    if not result.get("status"):
        status_code = 402 if "payment" in str(result.get("message") or "").lower() else 400
        return _err(result.get("message") or "ProcessBooking failed", status_code=status_code)
    return _ok(result.get("data") or {}, result.get("message") or "Success")


async def _get_booking_details(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    app_ref = str(body.get("app_reference") or body.get("AppReference") or "").strip()
    result = await blender.get_booking_details(app_ref)
    if not result.get("status"):
        return _err(result.get("message") or "Booking not found", status_code=404)
    return _ok(result.get("data") or {}, result.get("message") or "Success")


async def _refresh_booking_status(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    app_ref = str(body.get("app_reference") or body.get("AppReference") or "").strip()
    result = await blender.refresh_booking_status(app_ref)
    if not result.get("status"):
        return _err(result.get("message") or "Refresh failed")
    return _ok(result.get("data") or {}, result.get("message") or "Success")


async def _cancel_booking(
    body: dict[str, Any],
    session: AsyncSession,
    blender: FlightBlender,
    request: Request,
) -> JSONResponse:
    app_ref = str(body.get("app_reference") or body.get("AppReference") or "").strip()
    result = await blender.cancel_booking(app_ref)
    if not result.get("status"):
        return _err(result.get("message") or "Cancel failed")
    return _ok(result.get("data") or {}, result.get("message") or "Success")
