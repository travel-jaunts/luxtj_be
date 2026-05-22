from luxtj.application.dto.marketing import CreateCampaignDTO, UpdateCampaignDTO
from luxtj.application.interface.event import IDomainEventPublisher
from luxtj.domains.event.marketing import DEMarketingCampaignCreated
from luxtj.domains.model import MarketingCampaign
from luxtj.domains.repository.marketing import IMarketingRepository


class MarketingService:
    def __init__(
        self, marketing_repository: IMarketingRepository, event_publisher: IDomainEventPublisher
    ):
        self.marketing_repository = marketing_repository
        self.event_publisher = event_publisher

    async def list_campaigns(self) -> list[MarketingCampaign]:
        # Logic to list all marketing campaigns
        campaigns = await self.marketing_repository.list()
        return campaigns

    async def create_campaign(self, campaign_data: CreateCampaignDTO) -> MarketingCampaign:
        # Logic to create a marketing campaign
        campaign = await self.marketing_repository.create(campaign_data)
        # raise a domain event for created market
        await self.event_publisher.publish(self._new_marketing_campaign_event(campaign))

        return campaign

    async def get_campaign(self, campaign_id: str) -> MarketingCampaign:
        # Logic to retrieve a marketing campaign by ID
        campaign = await self.marketing_repository.get_by_id(campaign_id)
        return campaign

    async def update_campaign(
        self, campaign_id: str, update_data: UpdateCampaignDTO
    ) -> MarketingCampaign:
        # Logic to update a marketing campaign
        updated_campaign = await self.marketing_repository.update(campaign_id, update_data)
        return updated_campaign

    async def delete_campaign(self, campaign_id: str) -> MarketingCampaign:
        # Logic to delete a marketing campaign
        deleted_campaign = await self.marketing_repository.delete(campaign_id)
        return deleted_campaign

    def _new_marketing_campaign_event(
        self, campaign: MarketingCampaign
    ) -> DEMarketingCampaignCreated:
        new_campaign_event = DEMarketingCampaignCreated.from_campaign(campaign)
        new_campaign_event.source = "luxtj.domain.service.marketing.MarketingService"
        return new_campaign_event
