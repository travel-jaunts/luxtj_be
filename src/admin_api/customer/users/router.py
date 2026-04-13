from typing import Annotated

from fastapi import APIRouter, Body, Depends

from admin_api.customer.users.serializers import (
    CustomerBizKpiSummary,
    CustomerListItem,
    NewUserDetailsBody,
    # SignupOptionParams,
    UpdateUserDetailsBody,
)
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


@user_router.post(
    "/create-new-user",
    response_model=ApiSuccessResponse[CustomerListItem],
    status_code=200,
    summary="Create a new customer user",
    name="Create New Customer User",
)
async def create_new_customer_user(
    customer_service: Annotated[CustomerUserService, Depends(CustomerUserService)],
    # signup_options: Annotated[SignupOptionParams, Depends()],
    new_user_details: Annotated[NewUserDetailsBody, Body(...)],
) -> ApiSuccessResponse[CustomerListItem]:
    """
    Create a new customer user
    """
    # TODO: access control: restrict this endpoint to admin users only
    new_customer = await customer_service.create_new_user(
        new_user_details.first_name,
        new_user_details.last_name,
        new_user_details.phone_number,
        new_user_details.email,
        # signup_options=signup_options,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CustomerListItem.from_domain_model(new_customer),
    )


@user_router.post(
    "/{customer_id}/update",
    response_model=ApiSuccessResponse[CustomerListItem],
    status_code=200,
    summary="Update an existing customer user",
    name="Update Customer User",
)
async def update_customer_user(
    customer_id: str,
    customer_service: Annotated[CustomerUserService, Depends(CustomerUserService)],
    update_details: Annotated[UpdateUserDetailsBody, Body(...)],
) -> ApiSuccessResponse[CustomerListItem]:
    """
    Update an existing customer user
    """
    # TODO: access control: restrict this endpoint to admin users only
    updated_customer = await customer_service.update_user(
        customer_id=customer_id,
        update_user_dto=update_details.to_dto()
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CustomerListItem.from_domain_model(updated_customer),
    )


@user_router.post(
    "/{customer_id}/delete",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Delete a customer user",
    name="Delete Customer User",
)
async def delete_customer_user(
    customer_id: str,
    customer_service: Annotated[CustomerUserService, Depends(CustomerUserService)],
) -> ApiSuccessResponse[str]:
    """
    Delete a customer user
    """
    # TODO: access control: restrict this endpoint to admin users only
    await customer_service.delete_user(customer_id=customer_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Customer user {customer_id} has been deleted.",
    )
