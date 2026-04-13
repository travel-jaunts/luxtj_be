from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from admin_api.partner.property.serializers import (
    PartnerBizKpiSummary,
    PropertyPartnerDetails,
    PropertyPartnerLineItem,
    UpdatePropertyPartnerDetailsBody,
)
from admin_api.partner.property.service import PartnerService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)
from luxtj.domain.enums import PartnerStatusControlActionEnum

property_partner_router = APIRouter()


@property_partner_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[PartnerBizKpiSummary],
    status_code=200,
    summary="Get partners KPI summary",
    name="Partner KPI Summary",
)
async def property_partner_kpi_summary(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
) -> ApiSuccessResponse[PartnerBizKpiSummary]:
    """
    Get partner KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await partner_service.get_biz_kpi_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PartnerBizKpiSummary.from_domain_model(kpi_summary),
    )


@property_partner_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[PropertyPartnerLineItem]],
    status_code=200,
    summary="Get list of partners KPI summaries",
    name="List Partner KPI Summaries",
)
async def list_property_partners(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[PropertyPartnerLineItem]]:
    """
    Get list of property partners
    """
    # TODO: access control: restrict this endpoint to admin users only

    property_partners_list, pagination_meta = await partner_service.get_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[PropertyPartnerLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                PropertyPartnerLineItem.from_domain_model(partner)
                for partner in property_partners_list
            ],
        ),
    )


@property_partner_router.post(
    "/{partner_id}/details",
    response_model=ApiSuccessResponse[PropertyPartnerDetails],
    status_code=200,
    summary="Get detailed information about a specific property partner",
    name="Property Partner Details",
)
async def property_partner_details(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    partner_id: str,
) -> ApiSuccessResponse[PropertyPartnerDetails]:
    """
    Get detailed information about a specific property partner
    """
    # TODO: access control: restrict this endpoint to admin users only
    partner_details = await partner_service.get_details(partner_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PropertyPartnerDetails.from_domain_model(partner_details),
    )


@property_partner_router.post(
    "/{partner_id}/details-update",
    response_model=ApiSuccessResponse[PropertyPartnerDetails],
    status_code=200,
    summary="Update detailed information about a specific property partner",
    name="Property Partner Details Update",
)
async def property_partner_details_update(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    partner_id: str,
    update_details: Annotated[UpdatePropertyPartnerDetailsBody, Body(...)],
) -> ApiSuccessResponse[PropertyPartnerDetails]:
    # TODO: access control: restrict this endpoint to admin users only
    updated_partner = await partner_service.update_details(
        partner_id=partner_id, update_dto=update_details.to_dto()
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PropertyPartnerDetails.from_domain_model(updated_partner),
    )


@property_partner_router.post(
    "/{partner_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for a property partner",
    name="Property Partner Status Update",
)
async def property_partner_status_control(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    updated_status: Annotated[PartnerStatusControlActionEnum, Query(..., alias="to")],
    partner_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await partner_service.update_status(partner_id=partner_id, action=updated_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Property partner {partner_id} status updated to '{updated_status}' successfully",
    )
