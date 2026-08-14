"""Admin API — flight booking reports."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from admin_api.reports.flight_bookings.serializers import (
    FlightBookingDetailsBody,
    FlightBookingDetailSerializer,
    FlightBookingListFilters,
    FlightBookingListResultSerializer,
    FlightBookingRefreshBody,
)
from admin_api.reports.flight_bookings.service import FlightBookingReportsService
from luxtj.contexts.flight.application.blender import FlightBlender
from luxtj.contexts.identity.presentation.http.dependencies import require_permission
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiSerializerBaseModel,
    ApiSuccessResponse,
    RequestProcessStatus,
)

flight_bookings_router = APIRouter(
    prefix="/flight-bookings",
    tags=["admin_reports_flight_bookings"],
    dependencies=[Depends(require_permission("reports.flight_bookings.view"))],
)


class FlightBookingCancelBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., alias="appReference", min_length=1)


class FlightBookingCancelResultSerializer(ApiSerializerBaseModel):
    app_reference: str
    status: str
    message: str
    already_cancelled: bool = False


def _reports_service(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> FlightBookingReportsService:
    return FlightBookingReportsService(session)


def _blender(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    http_client: Annotated[Any, Depends(http_client_handle)],
) -> FlightBlender:
    return FlightBlender(session, http_client=http_client)


@flight_bookings_router.post(
    "/list",
    response_model=ApiSuccessResponse[FlightBookingListResultSerializer],
    summary="List flight bookings for admin reports",
)
async def list_flight_bookings(
    body: Annotated[FlightBookingListFilters, Body(...)],
    service: Annotated[FlightBookingReportsService, Depends(_reports_service)],
) -> ApiSuccessResponse[FlightBookingListResultSerializer]:
    if body.from_date and body.to_date and body.from_date > body.to_date:
        raise HTTPException(status_code=422, detail="from_date must be before or equal to to_date")
    result = await service.list_bookings(body)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=result)


@flight_bookings_router.post(
    "/details",
    response_model=ApiSuccessResponse[FlightBookingDetailSerializer],
    summary="Get flight booking detail for admin reports",
)
async def flight_booking_details(
    body: Annotated[FlightBookingDetailsBody, Body(...)],
    service: Annotated[FlightBookingReportsService, Depends(_reports_service)],
) -> ApiSuccessResponse[FlightBookingDetailSerializer]:
    detail = await service.get_details(body.app_reference)
    if detail is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=detail)


@flight_bookings_router.post(
    "/refresh-status",
    response_model=ApiSuccessResponse[FlightBookingDetailSerializer],
    summary="Refresh flight booking status from supplier",
)
async def refresh_flight_booking_status(
    body: Annotated[FlightBookingRefreshBody, Body(...)],
    blender: Annotated[FlightBlender, Depends(_blender)],
    service: Annotated[FlightBookingReportsService, Depends(_reports_service)],
) -> ApiSuccessResponse[FlightBookingDetailSerializer]:
    result = await blender.refresh_booking_status(body.app_reference)
    if not result.get("status"):
        raise HTTPException(
            status_code=400,
            detail=str(result.get("message") or "Refresh failed"),
        )
    detail = await service.get_details(body.app_reference)
    if detail is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=detail)


@flight_bookings_router.post(
    "/cancel",
    response_model=ApiSuccessResponse[FlightBookingCancelResultSerializer],
    summary="Cancel / VOID a flight booking via supplier",
    dependencies=[Depends(require_permission("reports.flight_bookings.cancel"))],
)
async def cancel_flight_booking(
    body: Annotated[FlightBookingCancelBody, Body(...)],
    blender: Annotated[FlightBlender, Depends(_blender)],
) -> ApiSuccessResponse[FlightBookingCancelResultSerializer]:
    result = await blender.cancel_booking(body.app_reference)
    if not result.get("status"):
        raise HTTPException(
            status_code=400,
            detail=str(result.get("message") or "Cancel failed"),
        )
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=FlightBookingCancelResultSerializer(
            app_reference=str(data.get("app_reference") or body.app_reference),
            status=str(data.get("status") or "BOOKING_CANCELLED"),
            message=str(result.get("message") or "Booking cancelled"),
            already_cancelled=bool(result.get("already_cancelled")),
        ),
    )


@flight_bookings_router.post(
    "/export",
    summary="Export flight bookings as CSV",
)
async def export_flight_bookings(
    body: Annotated[FlightBookingListFilters, Body(...)],
    service: Annotated[FlightBookingReportsService, Depends(_reports_service)],
) -> Response:
    if body.from_date and body.to_date and body.from_date > body.to_date:
        raise HTTPException(status_code=422, detail="from_date must be before or equal to to_date")
    csv_text = await service.export_csv(body)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="flight-bookings.csv"',
        },
    )
