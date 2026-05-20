from typing import Annotated

from fastapi import APIRouter, Body, Depends

from admin_api.marketing.campaigns.serializers import (
    CampaignSerializer,
    CreateCampaignBody,
)
from admin_api.marketing.campaigns.service import build_marketing_service
from common.serializerlib import ApiSuccessResponse, RequestProcessStatus
from luxtj.application.dto.marketing import CreateCampaignDTO
from luxtj.domain.service.marketing import MarketingService

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
    response_model=ApiSuccessResponse[CampaignSerializer],
    status_code=200,
    summary="Create a campaign",
    name="Create Campaign",
)
async def create_campaign(
    marketing_service: Annotated[MarketingService, Depends(build_marketing_service)],
    create_campaign_body: Annotated[CreateCampaignBody, Body(...)],
) -> ApiSuccessResponse[CampaignSerializer]:

    new_campaign_dto = CreateCampaignDTO(
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

    campaign = await marketing_service.create_campaign(new_campaign_dto)

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=CampaignSerializer.from_campaign(campaign)
    )
