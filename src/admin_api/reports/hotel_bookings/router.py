"""Admin API — hotel booking reports."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from admin_api.reports.hotel_bookings.serializers import (
    HotelBookingDetailsBody,
    HotelBookingDetailSerializer,
    HotelBookingListFilters,
    HotelBookingListResultSerializer,
    HotelBookingRefreshBody,
)
from admin_api.reports.hotel_bookings.service import HotelBookingReportsService
from luxtj.contexts.hotel.application.blender import HotelBlender
from luxtj.contexts.identity.presentation.http.dependencies import require_permission
from luxtj.shared_kernel.presentation.http.dependencies import (
    crs_database_session_handle,
    database_session_handle,
    http_client_handle,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiSerializerBaseModel,
    ApiSuccessResponse,
    RequestProcessStatus,
)

hotel_bookings_router = APIRouter(
    prefix="/hotel-bookings",
    tags=["admin_reports_hotel_bookings"],
    dependencies=[Depends(require_permission("reports.hotel_bookings.view"))],
)


class HotelBookingCancelBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., alias="appReference", min_length=1)


class HotelBookingCancelResultSerializer(ApiSerializerBaseModel):
    app_reference: str
    status: str
    message: str
    already_cancelled: bool = False


def _reports_service(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    crs_session: Annotated[AsyncSession, Depends(crs_database_session_handle)],
) -> HotelBookingReportsService:
    return HotelBookingReportsService(session, crs_session=crs_session)


def _blender(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    crs_session: Annotated[AsyncSession, Depends(crs_database_session_handle)],
    http_client: Annotated[Any, Depends(http_client_handle)],
) -> HotelBlender:
    return HotelBlender(session, crs_session=crs_session, http_client=http_client)


@hotel_bookings_router.post(
    "/list",
    response_model=ApiSuccessResponse[HotelBookingListResultSerializer],
    summary="List hotel bookings for admin reports",
)
async def list_hotel_bookings(
    body: Annotated[HotelBookingListFilters, Body(...)],
    service: Annotated[HotelBookingReportsService, Depends(_reports_service)],
) -> ApiSuccessResponse[HotelBookingListResultSerializer]:
    if body.from_date and body.to_date and body.from_date > body.to_date:
        raise HTTPException(status_code=422, detail="from_date must be before or equal to to_date")
    result = await service.list_bookings(body)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=result)


@hotel_bookings_router.post(
    "/details",
    response_model=ApiSuccessResponse[HotelBookingDetailSerializer],
    summary="Get hotel booking detail for admin reports",
)
async def hotel_booking_details(
    body: Annotated[HotelBookingDetailsBody, Body(...)],
    service: Annotated[HotelBookingReportsService, Depends(_reports_service)],
) -> ApiSuccessResponse[HotelBookingDetailSerializer]:
    detail = await service.get_details(body.app_reference)
    if detail is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=detail)


@hotel_bookings_router.post(
    "/refresh-status",
    response_model=ApiSuccessResponse[HotelBookingDetailSerializer],
    summary="Refresh hotel booking status from supplier",
)
async def refresh_hotel_booking_status(
    body: Annotated[HotelBookingRefreshBody, Body(...)],
    blender: Annotated[HotelBlender, Depends(_blender)],
    service: Annotated[HotelBookingReportsService, Depends(_reports_service)],
) -> ApiSuccessResponse[HotelBookingDetailSerializer]:
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


@hotel_bookings_router.post(
    "/cancel",
    response_model=ApiSuccessResponse[HotelBookingCancelResultSerializer],
    summary="Cancel a hotel booking via supplier",
    dependencies=[Depends(require_permission("reports.hotel_bookings.cancel"))],
)
async def cancel_hotel_booking(
    body: Annotated[HotelBookingCancelBody, Body(...)],
    blender: Annotated[HotelBlender, Depends(_blender)],
) -> ApiSuccessResponse[HotelBookingCancelResultSerializer]:
    result = await blender.cancel_booking(body.app_reference)
    if not result.get("status"):
        raise HTTPException(
            status_code=400,
            detail=str(result.get("message") or "Cancel failed"),
        )
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=HotelBookingCancelResultSerializer(
            app_reference=str(data.get("app_reference") or body.app_reference),
            status=str(data.get("status") or "CANCELLED"),
            message=str(result.get("message") or "Booking cancelled"),
            already_cancelled=bool(result.get("already_cancelled")),
        ),
    )


@hotel_bookings_router.post(
    "/export",
    summary="Export hotel bookings as CSV",
)
async def export_hotel_bookings(
    body: Annotated[HotelBookingListFilters, Body(...)],
    service: Annotated[HotelBookingReportsService, Depends(_reports_service)],
) -> Response:
    if body.from_date and body.to_date and body.from_date > body.to_date:
        raise HTTPException(status_code=422, detail="from_date must be before or equal to to_date")
    csv_text = await service.export_csv(body)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="hotel-bookings.csv"',
        },
    )
