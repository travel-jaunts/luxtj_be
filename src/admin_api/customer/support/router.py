from typing import Annotated

from fastapi import APIRouter, Body, Depends

from admin_api.customer.support.serializers import (
    AssignAgentBody,
    ResolveTicketBody,
    SupportKpiSummarySerializer,
    SupportTicketLineItem,
)
from admin_api.customer.support.service import CustomerSupportService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)

support_router = APIRouter(prefix="/support")


@support_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[SupportKpiSummarySerializer],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
async def customer_support_kpi_summary(
    support_service: Annotated[CustomerSupportService, Depends(CustomerSupportService)],
) -> ApiSuccessResponse[SupportKpiSummarySerializer]:
    """
    Get customer KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    support_kpi_summary = await support_service.get_kpi_summary()

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
async def list_customer_support_tickets(
    support_service: Annotated[CustomerSupportService, Depends(CustomerSupportService)],
    query: Annotated[PaginationParams, Depends()],
    search_filter: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[SupportTicketLineItem]]:
    """
    List support tickets for all customers with pagination
    """
    # TODO: access control: restrict this endpoint to support users only
    support_ticket_list, pagination_meta = await support_service.get_support_tickets(
        page=query.page,
        page_size=query.size,
        from_date=search_filter.from_date,
        to_date=search_filter.to_date,
        search_query=search_filter.search_query,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                SupportTicketLineItem.from_domain_model(ticket) for ticket in support_ticket_list
            ],
        ),
    )


@support_router.post(
    "/tickets/{ticket_id}/assign-agent",
    response_model=ApiSuccessResponse[SupportTicketLineItem],
    status_code=200,
    summary="Assign an agent to a support ticket",
    name="Assign Support Ticket Agent",
)
async def assign_support_ticket_agent(
    ticket_id: str,
    support_service: Annotated[CustomerSupportService, Depends(CustomerSupportService)],
    body: Annotated[AssignAgentBody, Body(...)],
) -> ApiSuccessResponse[SupportTicketLineItem]:
    """
    Assign an agent to an existing support ticket
    """
    # TODO: access control: restrict this endpoint to admin/support manager users only
    updated_ticket = await support_service.assign_agent(
        ticket_id=ticket_id,
        agent_id=body.agent_id,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=SupportTicketLineItem.from_domain_model(updated_ticket),
    )


@support_router.post(
    "/tickets/{ticket_id}/resolve",
    response_model=ApiSuccessResponse[SupportTicketLineItem],
    status_code=200,
    summary="Resolve a support ticket",
    name="Resolve Support Ticket",
)
async def resolve_support_ticket(
    ticket_id: str,
    support_service: Annotated[CustomerSupportService, Depends(CustomerSupportService)],
    body: Annotated[ResolveTicketBody, Body(...)],
) -> ApiSuccessResponse[SupportTicketLineItem]:
    """
    Mark a support ticket as resolved
    """
    # TODO: access control: restrict this endpoint to support users only
    resolved_ticket = await support_service.resolve_ticket(
        ticket_id=ticket_id,
        resolution_note=body.resolution_note,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=SupportTicketLineItem.from_domain_model(resolved_ticket),
    )
