from typing import Annotated

from fastapi import APIRouter, Body, Depends

from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
    DuplicateCampaignCommand,
    PauseCampaignCommand,
    UpdateCampaignCommand,
)
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.bootstrap import build_marketing_service
from luxtj.contexts.marketing.domain.errors import CampaignPolicyViolationError
from luxtj.contexts.marketing.presentation.http.schemas import (
    CampaignSerializer,
    CreateCampaignBody,
    UpdateCampaignBody,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

router = APIRouter()


@router.post(
    "/create",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Create a campaign",
    name="Create Campaign",
)
async def create_campaign(
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
    body: Annotated[CreateCampaignBody, Body(...)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    command = CreateCampaignCommand(
        name=body.campaign_name,
        description=body.description,
        channel=body.channel,
        audience_segments=body.audience.segments,
        audience_user_ids=body.audience.specific_users,
        content_template=body.content.template,
        start_date=body.schedule.start_date,
        frequency=body.schedule.frequency,
        frequency_schedule=body.schedule.frequency_schedule,
    )
    try:
        campaign = await marketing_service.create_campaign(command)
    except CampaignPolicyViolationError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CampaignSerializer.from_campaign(campaign),
    )


@router.post(
    "/{campaign_id}/update",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Update a campaign",
    name="Update Campaign",
)
async def update_campaign(
    campaign_id: str,
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
    body: Annotated[UpdateCampaignBody, Body(...)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    command = UpdateCampaignCommand(
        id=campaign_id,
        name=body.campaign_name,
        description=body.description,
        channel=body.channel,
        audience_user_ids=body.audience_user_ids,
        content_template=body.content_template,
        start_date=body.start_date,
        frequency=body.frequency,
        frequency_schedule=body.frequency_schedule,
        status=body.status,
    )
    try:
        campaign = await marketing_service.update_campaign(command)
    except KeyError:
        return ApiErrorResponse(error_message=f"Campaign {campaign_id} not found")
    except CampaignPolicyViolationError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CampaignSerializer.from_campaign(campaign),
    )


@router.post(
    "/{campaign_id}/duplicate",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Duplicate a campaign",
    name="Duplicate Campaign",
)
async def duplicate_campaign(
    campaign_id: str,
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    try:
        campaign = await marketing_service.duplicate_campaign(DuplicateCampaignCommand(id=campaign_id))
    except KeyError:
        return ApiErrorResponse(error_message=f"Campaign {campaign_id} not found")

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CampaignSerializer.from_campaign(campaign),
    )


@router.post(
    "/{campaign_id}/pause",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Pause a campaign",
    name="Pause Campaign",
)
async def pause_campaign(
    campaign_id: str,
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    try:
        campaign = await marketing_service.pause_campaign(PauseCampaignCommand(id=campaign_id))
    except KeyError:
        return ApiErrorResponse(error_message=f"Campaign {campaign_id} not found")

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CampaignSerializer.from_campaign(campaign),
    )


@router.post(
    "/{campaign_id}/delete",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Delete a campaign",
    name="Delete Campaign",
)
async def delete_campaign(
    campaign_id: str,
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    try:
        campaign = await marketing_service.delete_campaign(campaign_id)
    except KeyError:
        return ApiErrorResponse(error_message=f"Campaign {campaign_id} not found")

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CampaignSerializer.from_campaign(campaign),
    )
