from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.customer.bookings.serializers import BookingBizKpiSummary, CustomerBookingLineItem
from admin_api.customer.bookings.service import CustomerBookingService
from common.serializerlib import (
    ApiSuccessResponse,
    CurrencyQuery,
    PaginatedResult,
    PaginationParams,
    SearchFilterParams,
    RequestProcessStatus,
)

bookings_router = APIRouter(prefix="/bookings")


@bookings_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[BookingBizKpiSummary],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
async def bookings_kpi_summary(
    booking_service: Annotated[CustomerBookingService, Depends(CustomerBookingService)],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[BookingBizKpiSummary]:
    """
    Get customer KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await booking_service.get_biz_kpi_summary(iso_currency_str=iso_currency_str)

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=BookingBizKpiSummary.from_domain_model(kpi_summary),
    )


@bookings_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[CustomerBookingLineItem]],
    status_code=200,
    summary="List bookings for all customers with pagination and filtering",
    name="List Customer Bookings",
)
async def list_customer_bookings(
    booking_service: Annotated[CustomerBookingService, Depends(CustomerBookingService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[CustomerBookingLineItem]]:
    """
    List bookings for all customers with pagination
    """
    # TODO: access control: restrict this endpoint to admin users only
    customer_bookings_list, pagination_meta = await booking_service.get_list(
        page=page_query.page, 
        page_size=page_query.size, 
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
        iso_currency_str=iso_currency_str
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=pagination_meta.total,  # Replace with actual total count from database
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                CustomerBookingLineItem.from_domain_model(customer)
                for customer in customer_bookings_list
            ],
        ),
    )
