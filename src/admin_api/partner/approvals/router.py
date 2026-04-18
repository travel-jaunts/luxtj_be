from typing import Annotated

from fastapi import APIRouter, Depends, Query

from admin_api.partner.approvals.serializers import (
    ApprovalContentDetails,
    ApprovalKycDetails,
    ApprovalLineItem,
    ApprovalSummary,
    LifetimeApprovalSummary,
)
from admin_api.partner.approvals.service import PartnerApprovalsService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)
from luxtj.domain.enums import ApprovalControlActionEnum

approvals_router = APIRouter()


@approvals_router.post(
    "/summary",
    response_model=ApiSuccessResponse[ApprovalSummary],
    status_code=200,
    summary="Get partner approvals summary",
    name="Partner Approvals Summary",
)
async def approvals_summary(
    approvals_service: Annotated[PartnerApprovalsService, Depends(PartnerApprovalsService)],
) -> ApiSuccessResponse[ApprovalSummary]:
    # TODO: access control: restrict this endpoint to admin users only
    summary = await approvals_service.get_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ApprovalSummary.from_domain_model(summary),
    )


@approvals_router.post(
    "/lifetime-summary",
    response_model=ApiSuccessResponse[LifetimeApprovalSummary],
    status_code=200,
    summary="Get partner approvals lifetime summary",
    name="Partner Approvals Lifetime Summary",
)
async def approvals_lifetime_summary(
    approvals_service: Annotated[PartnerApprovalsService, Depends(PartnerApprovalsService)],
) -> ApiSuccessResponse[LifetimeApprovalSummary]:
    # TODO: access control: restrict this endpoint to admin users only
    summary = await approvals_service.get_lifetime_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=LifetimeApprovalSummary.from_domain_model(summary),
    )


@approvals_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[ApprovalLineItem]],
    status_code=200,
    summary="Get list of approvals",
    name="List Approvals",
)
async def approvals_list(
    approvals_service: Annotated[PartnerApprovalsService, Depends(PartnerApprovalsService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[ApprovalLineItem]]:
    # TODO: access control: restrict this endpoint to admin users only
    approvals_list_items, pagination_meta = await approvals_service.get_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[ApprovalLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[ApprovalLineItem.from_domain_model(item) for item in approvals_list_items],
        ),
    )


@approvals_router.post(
    "/{approval_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for an approval item",
    name="Approval Status Update",
)
async def approval_status_control(
    approvals_service: Annotated[PartnerApprovalsService, Depends(PartnerApprovalsService)],
    updated_status: Annotated[ApprovalControlActionEnum, Query(..., alias="to")],
    approval_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await approvals_service.update_status(approval_id=approval_id, action=updated_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Approval item {approval_id} status updated to '{updated_status}' successfully",
    )


@approvals_router.post(
    "/kyc/{approval_id}/details",
    response_model=ApiSuccessResponse[ApprovalKycDetails],
    status_code=200,
    summary="Get partner and KYC details for an approval item",
    name="Approval KYC Details",
)
async def approval_kyc_details(
    approvals_service: Annotated[PartnerApprovalsService, Depends(PartnerApprovalsService)],
    approval_id: str,
) -> ApiSuccessResponse[ApprovalKycDetails]:
    # TODO: access control: restrict this endpoint to admin users only
    details = await approvals_service.get_kyc_details(approval_id=approval_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ApprovalKycDetails.from_domain_model(details),
    )


@approvals_router.post(
    "/content/{approval_id}/details",
    response_model=ApiSuccessResponse[ApprovalContentDetails],
    status_code=200,
    summary="Get content details for an approval item",
    name="Approval Content Details",
)
async def approval_content_details(
    approvals_service: Annotated[PartnerApprovalsService, Depends(PartnerApprovalsService)],
    approval_id: str,
) -> ApiSuccessResponse[ApprovalContentDetails]:
    # TODO: access control: restrict this endpoint to admin users only
    content_details = await approvals_service.get_content_details(approval_id=approval_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ApprovalContentDetails.from_domain_model(content_details),
    )
