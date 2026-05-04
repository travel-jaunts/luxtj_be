from typing import Annotated

from fastapi import APIRouter, Depends, Query

from admin_api.reports.bookings.serializers import (
    BookingCustomerSearchQuery,
    BookingReport,
    BookingReportCustomerOption,
    BookingReportQuery,
)
from admin_api.reports.bookings.service import BookingReportService
from common.serializerlib import ApiSuccessResponse, CurrencyQuery, RequestProcessStatus

bookings_router = APIRouter(prefix="/bookings")


@bookings_router.post(
    "/data",
    response_model=ApiSuccessResponse[BookingReport],
    status_code=200,
    summary="Get bookings dashboard report data",
    name="Bookings Report Data",
)
async def booking_report_data(
    booking_report_service: Annotated[BookingReportService, Depends(BookingReportService)],
    report_query: Annotated[BookingReportQuery, Depends()],
    customer_ids: Annotated[
        list[str] | None,
        Query(
            alias="customerIds",
            description="Customer IDs used to limit booking overview or cancellation results",
        ),
    ] = None,
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[BookingReport]:
    """
    Get booking dashboard data using one common response shape for all booking report tabs.
    """
    # TODO: access control: restrict this endpoint to admin users only
    report = await booking_report_service.get_report(
        report_type=report_query.report_type,
        group_by=report_query.group_by,
        from_date=report_query.from_date,
        to_date=report_query.to_date,
        customer_ids=customer_ids,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=BookingReport.from_domain_model(report),
    )


@bookings_router.post(
    "/customers/search",
    response_model=ApiSuccessResponse[list[BookingReportCustomerOption]],
    status_code=200,
    summary="Search report customers",
    name="Search Report Customers",
)
async def search_report_customers(
    booking_report_service: Annotated[BookingReportService, Depends(BookingReportService)],
    customer_query: Annotated[BookingCustomerSearchQuery, Depends()],
) -> ApiSuccessResponse[list[BookingReportCustomerOption]]:
    """
    Search customer options for booking report filters.
    """
    # TODO: access control: restrict this endpoint to admin users only
    customers = await booking_report_service.search_customers(
        search_query=customer_query.search_query,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=[BookingReportCustomerOption.from_domain_model(customer) for customer in customers],
    )
