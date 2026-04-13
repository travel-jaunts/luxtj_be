from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from admin_api.partner.affiliate.serializers import (
    AffiliatePartnerBizKpiSummary,
    AffiliatePartnerDetails,
    AffiliatePartnerLineItem,
    UpdateAffiliatePartnerDetailsBody,
)
from admin_api.partner.affiliate.service import AffiliatePartnerService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)
from luxtj.domain.enums import PartnerStatusControlActionEnum

affiliate_partner_router = APIRouter()


@affiliate_partner_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[AffiliatePartnerBizKpiSummary],
    status_code=200,
    summary="Get affiliate partners KPI summary",
    name="Affiliate Partner KPI Summary",
)
async def affiliate_partner_kpi_summary(
    partner_service: Annotated[AffiliatePartnerService, Depends(AffiliatePartnerService)],
) -> ApiSuccessResponse[AffiliatePartnerBizKpiSummary]:
    """
    Get affiliate partner KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await partner_service.get_biz_kpi_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AffiliatePartnerBizKpiSummary.from_domain_model(kpi_summary),
    )


@affiliate_partner_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[AffiliatePartnerLineItem]],
    status_code=200,
    summary="Get list of affiliate partners",
    name="List Affiliate Partners",
)
async def list_affiliate_partners(
    partner_service: Annotated[AffiliatePartnerService, Depends(AffiliatePartnerService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[AffiliatePartnerLineItem]]:
    """
    Get list of affiliate partners
    """
    # TODO: access control: restrict this endpoint to admin users only

    affiliate_partners_list, pagination_meta = await partner_service.get_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[AffiliatePartnerLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                AffiliatePartnerLineItem.from_domain_model(partner)
                for partner in affiliate_partners_list
            ],
        ),
    )


@affiliate_partner_router.post(
    "/{partner_id}/details",
    response_model=ApiSuccessResponse[AffiliatePartnerDetails],
    status_code=200,
    summary="Get detailed information about a specific affiliate partner",
    name="Affiliate Partner Details",
)
async def affiliate_partner_details(
    partner_service: Annotated[AffiliatePartnerService, Depends(AffiliatePartnerService)],
    partner_id: str,
) -> ApiSuccessResponse[AffiliatePartnerDetails]:
    """
    Get detailed information about a specific affiliate partner
    """
    # TODO: access control: restrict this endpoint to admin users only
    partner_details = await partner_service.get_details(partner_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AffiliatePartnerDetails.from_domain_model(partner_details),
    )


@affiliate_partner_router.post(
    "/{partner_id}/details-update",
    response_model=ApiSuccessResponse[AffiliatePartnerDetails],
    status_code=200,
    summary="Update detailed information about a specific affiliate partner",
    name="Affiliate Partner Details Update",
)
async def affiliate_partner_details_update(
    partner_service: Annotated[AffiliatePartnerService, Depends(AffiliatePartnerService)],
    partner_id: str,
    update_details: Annotated[UpdateAffiliatePartnerDetailsBody, Body(...)],
) -> ApiSuccessResponse[AffiliatePartnerDetails]:
    # TODO: access control: restrict this endpoint to admin users only
    updated_partner = await partner_service.update_details(
        partner_id=partner_id, update_dto=update_details.to_dto()
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AffiliatePartnerDetails.from_domain_model(updated_partner),
    )


@affiliate_partner_router.post(
    "/{partner_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for an affiliate partner",
    name="Affiliate Partner Status Update",
)
async def affiliate_partner_status_control(
    partner_service: Annotated[AffiliatePartnerService, Depends(AffiliatePartnerService)],
    updated_status: Annotated[PartnerStatusControlActionEnum, Query(..., alias="to")],
    partner_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await partner_service.update_status(partner_id=partner_id, action=updated_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Affiliate partner {partner_id} status updated to '{updated_status}' successfully",
    )
