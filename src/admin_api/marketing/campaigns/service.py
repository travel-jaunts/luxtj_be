from typing import Annotated

from fastapi import Depends

from common.injectorlib import domain_event_publisher_handle
from luxtj.application.dto.marketing import CreateCampaignDTO, UpdateCampaignDTO
from luxtj.application.service.event import InProcessEventPublisher
from luxtj.domain.model import MarketingCampaign
from luxtj.domain.repository.marketing import IMarketingRepository
from luxtj.domain.service.marketing import MarketingService
from luxtj.utils import mockutils
from luxtj.utils.timeutils import datetime_now


class InMemoryMarketingRepository(IMarketingRepository):
    def __init__(self) -> None:
        self._campaigns: dict[str, MarketingCampaign] = {}

    async def list(self) -> list[MarketingCampaign]:
        return list(self._campaigns.values())

    async def create(self, campaign_data: CreateCampaignDTO) -> MarketingCampaign:
        campaign = MarketingCampaign(
            name=campaign_data.name,
            description=campaign_data.description,
            channel=campaign_data.channel,
            audience=mockutils.random_user_ids(2, 10),
            content=campaign_data.content_template,
            start_date=campaign_data.start_date,
            frequency=campaign_data.frequency,
            frequency_schedule=campaign_data.frequency_schedule,
            created_at=datetime_now(),
            updated_at=datetime_now(),
        )
        self._campaigns[str(campaign.id)] = campaign
        return campaign

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign:
        return self._campaigns[campaign_id]

    async def update(self, campaign_id: str, update_data: UpdateCampaignDTO) -> MarketingCampaign:
        campaign = self._campaigns[campaign_id]
        campaign.name = update_data.name
        campaign.description = update_data.description
        campaign.channel = update_data.channel
        campaign.audience = update_data.audience_user_ids
        campaign.content = update_data.content_template
        campaign.start_date = update_data.start_date
        campaign.frequency = update_data.frequency
        campaign.frequency_schedule = update_data.frequency_schedule
        campaign.updated_at = datetime_now()
        return campaign

    async def delete(self, campaign_id: str) -> MarketingCampaign:
        return self._campaigns.pop(campaign_id)


_MARKETING_REPOSITORY = InMemoryMarketingRepository()


def build_marketing_repository() -> IMarketingRepository:
    return _MARKETING_REPOSITORY


def build_marketing_service(
    event_publisher: Annotated[InProcessEventPublisher, Depends(domain_event_publisher_handle)],
    marketing_repository: Annotated[IMarketingRepository, Depends(build_marketing_repository)],
) -> MarketingService:
    return MarketingService(
        marketing_repository=marketing_repository,
        event_publisher=event_publisher,
    )
