from luxtj.application.interface.event import IDomainEventPublisher
from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
    UpdateCampaignCommand,
)
from luxtj.contexts.marketing.application.ports import AudienceResolver, MarketingRepository
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign


class MarketingService:
    def __init__(
        self,
        marketing_repository: MarketingRepository,
        event_publisher: IDomainEventPublisher,
        audience_resolver: AudienceResolver | None = None,
    ):
        self.marketing_repository = marketing_repository
        self.event_publisher = event_publisher
        self.audience_resolver = audience_resolver

    async def list_campaigns(self) -> list[MarketingCampaign]:
        return await self.marketing_repository.list()

    async def create_campaign(self, campaign_data: CreateCampaignCommand) -> MarketingCampaign:
        audience = await self._resolve_audience(campaign_data)
        campaign = MarketingCampaign.create(
            name=campaign_data.name,
            description=campaign_data.description,
            channel=campaign_data.channel,
            audience=audience,
            content=campaign_data.content_template,
            start_date=campaign_data.start_date,
            frequency=campaign_data.frequency,
            frequency_schedule=campaign_data.frequency_schedule,
        )

        campaign = await self.marketing_repository.add(campaign)
        for event in campaign.pull_events():
            await self.event_publisher.publish(event)

        return campaign

    async def get_campaign(self, campaign_id: str) -> MarketingCampaign:
        return await self.marketing_repository.get_by_id(campaign_id)

    async def update_campaign(
        self,
        campaign_id: str,
        update_data: UpdateCampaignCommand,
    ) -> MarketingCampaign:
        campaign = await self.marketing_repository.get_by_id(campaign_id)
        campaign.update(
            name=update_data.name,
            description=update_data.description,
            channel=update_data.channel,
            audience=update_data.audience_user_ids,
            content=update_data.content_template,
            start_date=update_data.start_date,
            frequency=update_data.frequency,
            frequency_schedule=update_data.frequency_schedule,
        )
        return await self.marketing_repository.save(campaign)

    async def delete_campaign(self, campaign_id: str) -> MarketingCampaign:
        return await self.marketing_repository.delete(campaign_id)

    async def _resolve_audience(self, campaign_data: CreateCampaignCommand) -> list[str]:
        if self.audience_resolver is None:
            return list(campaign_data.audience_user_ids)

        return await self.audience_resolver.resolve_campaign_audience(campaign_data)
