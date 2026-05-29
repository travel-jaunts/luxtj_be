from typing import Annotated

from fastapi import APIRouter, Body, Depends

from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
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

campaigns_router = APIRouter(prefix="/campaigns")


@campaigns_router.post(
    "/list",
    response_model=ApiSuccessResponse[list[CampaignSerializer]],
    status_code=200,
    summary="List all campaigns",
    name="List Campaigns",
)
async def list_campaigns(
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
) -> ApiSuccessResponse[list[CampaignSerializer]]:
    campaigns = await marketing_service.list_campaigns()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=[CampaignSerializer.from_campaign(campaign) for campaign in campaigns],
    )


@campaigns_router.post(
    "/create",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Create a campaign",
    name="Create Campaign",
)
async def create_campaign(
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
    create_campaign_body: Annotated[CreateCampaignBody, Body(...)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    command = CreateCampaignCommand(
        name=create_campaign_body.campaign_name,
        description=create_campaign_body.description,
        channel=create_campaign_body.channel,
        audience_segments=create_campaign_body.audience.segments,
        audience_user_ids=create_campaign_body.audience.specific_users,
        content_template=create_campaign_body.content.template,
        start_date=create_campaign_body.schedule.start_date,
        frequency=create_campaign_body.schedule.frequency,
        frequency_schedule=create_campaign_body.schedule.frequency_schedule,
    )

    try:
        campaign = await marketing_service.create_campaign(command)
    except CampaignPolicyViolationError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CampaignSerializer.from_campaign(campaign),
    )


@campaigns_router.post(
    "/{campaign_id}/update",
    response_model=ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Update a campaign",
    name="Update Campaign",
)
async def update_campaign(
    campaign_id: str,
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
    update_campaign_body: Annotated[UpdateCampaignBody, Body(...)],
) -> ApiSuccessResponse[CampaignSerializer] | ApiErrorResponse:
    command = UpdateCampaignCommand(
        id=campaign_id,
        name=update_campaign_body.campaign_name,
        description=update_campaign_body.description,
        channel=update_campaign_body.channel,
        audience_user_ids=update_campaign_body.audience_user_ids,
        content_template=update_campaign_body.content_template,
        start_date=update_campaign_body.start_date,
        frequency=update_campaign_body.frequency,
        frequency_schedule=update_campaign_body.frequency_schedule,
        status=update_campaign_body.status,
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


marketing_router = APIRouter(prefix="/marketing", tags=["admin_marketing"])
marketing_router.include_router(campaigns_router)
