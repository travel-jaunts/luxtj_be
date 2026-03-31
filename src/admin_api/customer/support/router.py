from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.customer.support.serializers import (
    SupportKpiSummarySerializer,
    SupportTicketLineItem,
)
from admin_api.customer.support.service import CustomerSupportService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
)

support_router = APIRouter(prefix="/support")


@support_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[SupportKpiSummarySerializer],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
def customer_support_kpi_summary(
    support_service: Annotated[CustomerSupportService, Depends(CustomerSupportService)],
) -> ApiSuccessResponse[SupportKpiSummarySerializer]:
    """
    Get customer KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    support_kpi_summary = support_service.get_kpi_summary()

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=SupportKpiSummarySerializer.from_domain_model(support_kpi_summary),
    )


@support_router.post(
    "/tickets/list",
    response_model=ApiSuccessResponse[PaginatedResult[SupportTicketLineItem]],
    status_code=200,
    summary="List support tickets for all customers with pagination and filtering",
    name="List Customer Support Tickets",
)
def list_customer_support_tickets(
    support_service: Annotated[CustomerSupportService, Depends(CustomerSupportService)],
    query: Annotated[PaginationParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[SupportTicketLineItem]]:
    """
    List support tickets for all customers with pagination
    """
    # TODO: access control: restrict this endpoint to support users only
    support_ticket_list, pagination_meta = support_service.get_support_tickets(
        page=query.page, page_size=query.size
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=pagination_meta.total,  # Replace with actual total count from database
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                SupportTicketLineItem.from_domain_model(ticket) for ticket in support_ticket_list
            ],
        ),
    )
