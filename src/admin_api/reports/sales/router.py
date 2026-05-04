from typing import Annotated

from fastapi import APIRouter, Depends, Query

from admin_api.reports.sales.serializers import (
    SalesDimensionOption,
    SalesDimensionSearchQuery,
    SalesReport,
    SalesReportQuery,
)
from admin_api.reports.sales.service import SalesReportService
from common.serializerlib import ApiSuccessResponse, CurrencyQuery, RequestProcessStatus

sales_router = APIRouter(prefix="/sales")


@sales_router.post(
    "/data",
    response_model=ApiSuccessResponse[SalesReport],
    status_code=200,
    summary="Get sales dashboard report data",
    name="Sales Report Data",
)
async def sales_report_data(
    sales_report_service: Annotated[SalesReportService, Depends(SalesReportService)],
    report_query: Annotated[SalesReportQuery, Depends()],
    destination_ids: Annotated[
        list[str] | None,
        Query(
            alias="destinationIds",
            description="Destination IDs used to limit destination sales results",
        ),
    ] = None,
    property_ids: Annotated[
        list[str] | None,
        Query(
            alias="propertyIds",
            description="Property IDs used to limit property sales results",
        ),
    ] = None,
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[SalesReport]:
    """
    Get sales dashboard data using one common response shape for all sales report tabs.
    """
    # TODO: access control: restrict this endpoint to admin users only
    report = await sales_report_service.get_report(
        report_type=report_query.report_type,
        from_date=report_query.from_date,
        to_date=report_query.to_date,
        destination_ids=destination_ids,
        property_ids=property_ids,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=SalesReport.from_domain_model(report),
    )


@sales_router.post(
    "/dimensions/search",
    response_model=ApiSuccessResponse[list[SalesDimensionOption]],
    status_code=200,
    summary="Search sales report dimensions",
    name="Search Sales Report Dimensions",
)
async def search_sales_report_dimensions(
    sales_report_service: Annotated[SalesReportService, Depends(SalesReportService)],
    dimension_query: Annotated[SalesDimensionSearchQuery, Depends()],
) -> ApiSuccessResponse[list[SalesDimensionOption]]:
    """
    Search destination or property options for report filters.
    """
    # TODO: access control: restrict this endpoint to admin users only
    dimensions = await sales_report_service.search_dimensions(
        dimension_type=dimension_query.dimension_type,
        search_query=dimension_query.search_query,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=[SalesDimensionOption.from_domain_model(dimension) for dimension in dimensions],
    )
