from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
    DuplicateCampaignCommand,
    PauseCampaignCommand,
    UpdateCampaignCommand,
)
from luxtj.contexts.marketing.application.ports import AudienceResolver, MarketingRepository
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.shared_kernel.application import DomainEventPublisher


class MarketingService:
    def __init__(
        self,
        marketing_repository: MarketingRepository,
        event_publisher: DomainEventPublisher,
        audience_resolver: AudienceResolver | None = None,
    ):
        self.marketing_repository = marketing_repository
        self.event_publisher = event_publisher
        self.audience_resolver = audience_resolver

    async def list_campaigns(self) -> list[MarketingCampaign]:
        return await self.marketing_repository.list()

    async def get_campaign(self, campaign_id: str) -> MarketingCampaign:
        return await self.marketing_repository.get_by_id(campaign_id)

    async def create_campaign(self, command: CreateCampaignCommand) -> MarketingCampaign:
        audience = await self._resolve_audience(command)
        campaign = MarketingCampaign.create(
            name=command.name,
            description=command.description,
            channel=command.channel,
            audience=audience,
            content=command.content_template,
            start_date=command.start_date,
            frequency=command.frequency,
            frequency_schedule=command.frequency_schedule,
        )
        campaign = await self.marketing_repository.add(campaign)
        await self._publish_pending_events(campaign)
        return campaign

    async def update_campaign(self, command: UpdateCampaignCommand) -> MarketingCampaign:
        campaign = await self.marketing_repository.get_by_id(command.id)
        campaign.update(
            name=command.name,
            description=command.description,
            channel=command.channel,
            audience=command.audience_user_ids,
            content=command.content_template,
            start_date=command.start_date,
            frequency=command.frequency,
            frequency_schedule=command.frequency_schedule,
            status=command.status,
        )
        campaign = await self.marketing_repository.save(campaign)
        await self._publish_pending_events(campaign)
        return campaign

    async def duplicate_campaign(self, command: DuplicateCampaignCommand) -> MarketingCampaign:
        source = await self.marketing_repository.get_by_id(command.id)
        duplicate = MarketingCampaign.duplicate(source)
        duplicate = await self.marketing_repository.add(duplicate)
        await self._publish_pending_events(duplicate)
        return duplicate

    async def pause_campaign(self, command: PauseCampaignCommand) -> MarketingCampaign:
        campaign = await self.marketing_repository.get_by_id(command.id)
        campaign.pause()
        campaign = await self.marketing_repository.save(campaign)
        await self._publish_pending_events(campaign)
        return campaign

    async def delete_campaign(self, campaign_id: str) -> MarketingCampaign:
        campaign = await self.marketing_repository.delete(campaign_id)
        campaign.delete()
        await self._publish_pending_events(campaign)
        return campaign

    async def _publish_pending_events(self, campaign: MarketingCampaign) -> None:
        for event in campaign.pull_events():
            await self.event_publisher.publish(event)

    async def _resolve_audience(self, command: CreateCampaignCommand) -> list[str]:
        if self.audience_resolver is None:
            return list(command.audience_user_ids)
        return await self.audience_resolver.resolve_campaign_audience(command)
