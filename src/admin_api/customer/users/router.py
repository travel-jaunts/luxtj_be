from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.customer.users.serializers import CustomerBizKpiSummary, CustomerListItem
from admin_api.customer.users.service import CustomerUserService
from common.serializerlib import (
    ApiSuccessResponse,
    CurrencyQuery,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
)

user_router = APIRouter()


@user_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[CustomerBizKpiSummary],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
async def customer_kpi_summary(
    customer_service: Annotated[CustomerUserService, Depends(CustomerUserService)],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[CustomerBizKpiSummary]:
    """
    Get customer KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await customer_service.get_biz_kpi_summary(iso_currency_str=iso_currency_str)

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CustomerBizKpiSummary.from_domain_model(kpi_summary),
    )


@user_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[CustomerListItem]],
    status_code=200,
    summary="List customers with pagination and filtering",
    name="List Customers",
)
async def list_customers(
    customer_service: Annotated[CustomerUserService, Depends(CustomerUserService)],
    query: Annotated[PaginationParams, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[CustomerListItem]]:
    """
    List customers with pagination
    """
    # TODO: access control: restrict this endpoint to admin users only
    person_list, pagination_meta = await customer_service.get_list(
        page=query.page, page_size=query.size, iso_currency_str=iso_currency_str
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=pagination_meta.total,  # Replace with actual total count from database
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[CustomerListItem.from_domain_model(customer) for customer in person_list],
        ),
    )
