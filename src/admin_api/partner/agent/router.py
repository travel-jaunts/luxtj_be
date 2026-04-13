from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from admin_api.partner.agent.serializers import (
    AgentPartnerBizKpiSummary,
    AgentPartnerDetails,
    AgentPartnerLineItem,
    UpdateAgentPartnerDetailsBody,
)
from admin_api.partner.agent.service import AgentPartnerService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)
from luxtj.domain.enums import PartnerStatusControlActionEnum

agent_partner_router = APIRouter()


@agent_partner_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[AgentPartnerBizKpiSummary],
    status_code=200,
    summary="Get agent partners KPI summary",
    name="Agent Partner KPI Summary",
)
async def agent_partner_kpi_summary(
    partner_service: Annotated[AgentPartnerService, Depends(AgentPartnerService)],
) -> ApiSuccessResponse[AgentPartnerBizKpiSummary]:
    """
    Get agent partner KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await partner_service.get_biz_kpi_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AgentPartnerBizKpiSummary.from_domain_model(kpi_summary),
    )


@agent_partner_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[AgentPartnerLineItem]],
    status_code=200,
    summary="Get list of agent partners",
    name="List Agent Partners",
)
async def list_agent_partners(
    partner_service: Annotated[AgentPartnerService, Depends(AgentPartnerService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[AgentPartnerLineItem]]:
    """
    Get list of agent partners
    """
    # TODO: access control: restrict this endpoint to admin users only

    agent_partners_list, pagination_meta = await partner_service.get_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[AgentPartnerLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                AgentPartnerLineItem.from_domain_model(partner) for partner in agent_partners_list
            ],
        ),
    )


@agent_partner_router.post(
    "/{partner_id}/details",
    response_model=ApiSuccessResponse[AgentPartnerDetails],
    status_code=200,
    summary="Get detailed information about a specific agent partner",
    name="Agent Partner Details",
)
async def agent_partner_details(
    partner_service: Annotated[AgentPartnerService, Depends(AgentPartnerService)],
    partner_id: str,
) -> ApiSuccessResponse[AgentPartnerDetails]:
    """
    Get detailed information about a specific agent partner
    """
    # TODO: access control: restrict this endpoint to admin users only
    partner_details = await partner_service.get_details(partner_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AgentPartnerDetails.from_domain_model(partner_details),
    )


@agent_partner_router.post(
    "/{partner_id}/details-update",
    response_model=ApiSuccessResponse[AgentPartnerDetails],
    status_code=200,
    summary="Update detailed information about a specific agent partner",
    name="Agent Partner Details Update",
)
async def agent_partner_details_update(
    partner_service: Annotated[AgentPartnerService, Depends(AgentPartnerService)],
    partner_id: str,
    update_details: Annotated[UpdateAgentPartnerDetailsBody, Body(...)],
) -> ApiSuccessResponse[AgentPartnerDetails]:
    # TODO: access control: restrict this endpoint to admin users only
    updated_partner = await partner_service.update_details(
        partner_id=partner_id, update_dto=update_details.to_dto()
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AgentPartnerDetails.from_domain_model(updated_partner),
    )


@agent_partner_router.post(
    "/{partner_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for an agent partner",
    name="Agent Partner Status Update",
)
async def agent_partner_status_control(
    partner_service: Annotated[AgentPartnerService, Depends(AgentPartnerService)],
    updated_status: Annotated[PartnerStatusControlActionEnum, Query(..., alias="to")],
    partner_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await partner_service.update_status(partner_id=partner_id, action=updated_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Agent partner {partner_id} status updated to '{updated_status}' successfully",
    )
