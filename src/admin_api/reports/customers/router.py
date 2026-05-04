from typing import Annotated

from fastapi import APIRouter, Depends, Query

from admin_api.reports.customers.serializers import (
    CustomerOverview,
    CustomerOverviewQuery,
    CustomerSatisfactionReport,
    CustomerValueReport,
)
from admin_api.reports.customers.service import CustomerReportService
from common.serializerlib import ApiSuccessResponse, CurrencyQuery, RequestProcessStatus

customers_router = APIRouter(prefix="/customers")


@customers_router.post(
    "/overview/data",
    response_model=ApiSuccessResponse[CustomerOverview],
    status_code=200,
    summary="Get customer overview report data",
    name="Customer Overview Report Data",
)
async def customer_overview_data(
    customer_report_service: Annotated[CustomerReportService, Depends(CustomerReportService)],
    overview_query: Annotated[CustomerOverviewQuery, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[CustomerOverview]:
    """
    Get aggregate customer overview metrics for the dashboard.
    """
    # TODO: access control: restrict this endpoint to admin users only
    overview = await customer_report_service.get_overview(
        from_date=overview_query.from_date,
        to_date=overview_query.to_date,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CustomerOverview.from_domain_model(overview),
    )


@customers_router.post(
    "/value/data",
    response_model=ApiSuccessResponse[CustomerValueReport],
    status_code=200,
    summary="Get customer value report data",
    name="Customer Value Report Data",
)
async def customer_value_data(
    customer_report_service: Annotated[CustomerReportService, Depends(CustomerReportService)],
    customer_ids: Annotated[
        list[str] | None,
        Query(
            alias="customerIds",
            description="Customer IDs used to limit customer value results",
        ),
    ] = None,
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[CustomerValueReport]:
    """
    Get customer value metrics by customer.
    """
    # TODO: access control: restrict this endpoint to admin users only
    customer_value = await customer_report_service.get_customer_value(
        customer_ids=customer_ids,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CustomerValueReport.from_domain_model(customer_value),
    )


@customers_router.post(
    "/satisfaction/{customer_id}",
    response_model=ApiSuccessResponse[CustomerSatisfactionReport],
    status_code=200,
    summary="Get customer satisfaction report data",
    name="Customer Satisfaction Report Data",
)
async def customer_satisfaction_data(
    customer_id: str,
    customer_report_service: Annotated[CustomerReportService, Depends(CustomerReportService)],
) -> ApiSuccessResponse[CustomerSatisfactionReport]:
    """
    Get numeric customer satisfaction metrics for one customer.
    """
    # TODO: access control: restrict this endpoint to admin users only
    satisfaction = await customer_report_service.get_satisfaction(customer_id=customer_id)

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CustomerSatisfactionReport.from_domain_model(satisfaction),
    )
