from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
    CreateOfferCommand,
    DeleteOfferCommand,
    DuplicateCampaignCommand,
    PauseCampaignCommand,
    PauseOfferCommand,
    RescindOfferCommand,
    SearchOffersCommand,
    UpdateCampaignCommand,
)
from luxtj.contexts.marketing.application.ports import (
    AudienceResolver,
    MarketingRepository,
    OfferRepository,
)
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.offer import Offer
from luxtj.shared_kernel.application.event_bus import DomainEventPublisher


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
        await self._flush_events(campaign)
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
        await self._flush_events(campaign)
        return campaign

    async def duplicate_campaign(self, command: DuplicateCampaignCommand) -> MarketingCampaign:
        source = await self.marketing_repository.get_by_id(command.id)
        duplicate = MarketingCampaign.duplicate(source)
        duplicate = await self.marketing_repository.add(duplicate)
        await self._flush_events(duplicate)
        return duplicate

    async def pause_campaign(self, command: PauseCampaignCommand) -> MarketingCampaign:
        campaign = await self.marketing_repository.get_by_id(command.id)
        campaign.pause()
        campaign = await self.marketing_repository.save(campaign)
        await self._flush_events(campaign)
        return campaign

    async def delete_campaign(self, campaign_id: str) -> MarketingCampaign:
        campaign = await self.marketing_repository.delete(campaign_id)
        campaign.delete()
        await self._flush_events(campaign)
        return campaign

    async def _flush_events(self, *aggregates: MarketingCampaign) -> None:
        for aggregate in aggregates:
            for event in aggregate.pull_events():
                await self.event_publisher.publish(event)

    async def _resolve_audience(self, command: CreateCampaignCommand) -> list[str]:
        if self.audience_resolver is None:
            return list(command.audience_user_ids)
        return await self.audience_resolver.resolve_campaign_audience(command)


class OffersService:
    def __init__(
        self,
        repository: OfferRepository,
        event_publisher: DomainEventPublisher,
    ):
        self.repository = repository
        self.event_publisher = event_publisher

    async def create_offer(self, command: CreateOfferCommand) -> Offer:
        offer = Offer.create(
            name=command.name,
            code=command.code,
            type=command.type,
            discount_value=command.discount_value,
            min_booking_value=command.min_booking_value,
            min_booking_value_currency=command.min_booking_value_currency,
            validity_start=command.validity_start,
            validity_end=command.validity_end,
            usage_limit_per_user=command.usage_limit_per_user,
            applicability_on=command.applicability_on,
            stackable=command.stackable,
            auto_apply=command.auto_apply,
        )
        await self.repository.add(offer)
        await self._flush_events(offer)
        return offer

    async def search_offers(self, command: SearchOffersCommand) -> list[Offer]:
        return await self.repository.search(
            name=command.name,
            status=command.status,
            type=command.type,
        )

    async def pause_offer(self, command: PauseOfferCommand) -> Offer:
        offer = await self.repository.get_by_id(command.offer_id)
        offer.pause()
        await self.repository.save(offer)
        await self._flush_events(offer)
        return offer

    async def rescind_offer(self, command: RescindOfferCommand) -> Offer:
        offer = await self.repository.get_by_id(command.offer_id)
        offer.rescind()
        await self.repository.save(offer)
        await self._flush_events(offer)
        return offer

    async def delete_offer(self, command: DeleteOfferCommand) -> Offer:
        offer = await self.repository.get_by_id(command.offer_id)
        offer.delete()
        await self.repository.save(offer)
        await self._flush_events(offer)
        return offer

    async def _flush_events(self, *aggregates: Offer) -> None:
        for aggregate in aggregates:
            for event in aggregate.pull_events():
                await self.event_publisher.publish(event)
