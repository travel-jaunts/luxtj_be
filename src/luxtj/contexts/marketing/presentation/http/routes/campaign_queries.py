from typing import Annotated

from fastapi import APIRouter, Depends

from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.bootstrap import build_marketing_service
from luxtj.contexts.marketing.presentation.http.schemas import CampaignSerializer
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse, RequestProcessStatus

router = APIRouter()


@router.post(
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
