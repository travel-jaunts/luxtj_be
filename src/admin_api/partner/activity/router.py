from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from admin_api.partner.activity.serializers import (
    ActivityPartnerBizKpiSummary,
    ActivityPartnerDetails,
    ActivityPartnerLineItem,
    UpdateActivityPartnerDetailsBody,
)
from admin_api.partner.activity.service import ActivityPartnerService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)
from luxtj.domain.enums import PartnerStatusControlActionEnum

activity_partner_router = APIRouter()


@activity_partner_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[ActivityPartnerBizKpiSummary],
    status_code=200,
    summary="Get activity partners KPI summary",
    name="Activity Partner KPI Summary",
)
async def activity_partner_kpi_summary(
    partner_service: Annotated[ActivityPartnerService, Depends(ActivityPartnerService)],
) -> ApiSuccessResponse[ActivityPartnerBizKpiSummary]:
    """
    Get activity partner KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await partner_service.get_biz_kpi_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ActivityPartnerBizKpiSummary.from_domain_model(kpi_summary),
    )


@activity_partner_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[ActivityPartnerLineItem]],
    status_code=200,
    summary="Get list of activity partners",
    name="List Activity Partners",
)
async def list_activity_partners(
    partner_service: Annotated[ActivityPartnerService, Depends(ActivityPartnerService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[ActivityPartnerLineItem]]:
    """
    Get list of activity partners
    """
    # TODO: access control: restrict this endpoint to admin users only

    activity_partners_list, pagination_meta = await partner_service.get_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[ActivityPartnerLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                ActivityPartnerLineItem.from_domain_model(partner)
                for partner in activity_partners_list
            ],
        ),
    )


@activity_partner_router.post(
    "/{partner_id}/details",
    response_model=ApiSuccessResponse[ActivityPartnerDetails],
    status_code=200,
    summary="Get detailed information about a specific activity partner",
    name="Activity Partner Details",
)
async def activity_partner_details(
    partner_service: Annotated[ActivityPartnerService, Depends(ActivityPartnerService)],
    partner_id: str,
) -> ApiSuccessResponse[ActivityPartnerDetails]:
    """
    Get detailed information about a specific activity partner
    """
    # TODO: access control: restrict this endpoint to admin users only
    partner_details = await partner_service.get_details(partner_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ActivityPartnerDetails.from_domain_model(partner_details),
    )


@activity_partner_router.post(
    "/{partner_id}/details-update",
    response_model=ApiSuccessResponse[ActivityPartnerDetails],
    status_code=200,
    summary="Update detailed information about a specific activity partner",
    name="Activity Partner Details Update",
)
async def activity_partner_details_update(
    partner_service: Annotated[ActivityPartnerService, Depends(ActivityPartnerService)],
    partner_id: str,
    update_details: Annotated[UpdateActivityPartnerDetailsBody, Body(...)],
) -> ApiSuccessResponse[ActivityPartnerDetails]:
    # TODO: access control: restrict this endpoint to admin users only
    updated_partner = await partner_service.update_details(
        partner_id=partner_id, update_dto=update_details.to_dto()
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ActivityPartnerDetails.from_domain_model(updated_partner),
    )


@activity_partner_router.post(
    "/{partner_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for an activity partner",
    name="Activity Partner Status Update",
)
async def activity_partner_status_control(
    partner_service: Annotated[ActivityPartnerService, Depends(ActivityPartnerService)],
    updated_status: Annotated[PartnerStatusControlActionEnum, Query(..., alias="to")],
    partner_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await partner_service.update_status(partner_id=partner_id, action=updated_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Activity partner {partner_id} status updated to '{updated_status}' successfully",
    )
