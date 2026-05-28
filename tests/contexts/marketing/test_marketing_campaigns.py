import asyncio
from datetime import date

from luxtj.contexts.marketing.application.commands import CreateCampaignCommand
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)
from luxtj.contexts.marketing.infrastructure.persistence import (
    InMemoryMarketingRepository,
    MarketingCampaignRow,
)
from luxtj.shared_kernel.domain import BaseDomainEvent


class CapturingEventPublisher:
    def __init__(self) -> None:
        self.events: list[BaseDomainEvent] = []

    async def publish(self, event: BaseDomainEvent) -> None:
        self.events.append(event)


def test_create_campaign_persists_campaign_and_publishes_event() -> None:
    async def run_case() -> None:
        repository = InMemoryMarketingRepository()
        event_publisher = CapturingEventPublisher()
        service = MarketingService(
            marketing_repository=repository,
            event_publisher=event_publisher,
        )

        campaign = await service.create_campaign(
            CreateCampaignCommand(
                name="Summer Escapes",
                description="Promote luxury summer itineraries",
                channel=CampaignChannelEnum.EMAIL,
                audience_segments=[],
                audience_user_ids=["user-1", "user-2"],
                content_template="Hello {{ first_name }}",
                start_date=date(2026, 6, 1),
                frequency=ScheduleFrequencyEnum.ONE_TIME,
            )
        )

        assert campaign.status == CampaignStatusEnum.DRAFT
        assert campaign.audience == ["user-1", "user-2"]
        assert await repository.get_by_id(str(campaign.id)) == campaign
        assert len(event_publisher.events) == 1
        assert event_publisher.events[0].type == "com.luxtj.marketing.campaign.created.v1"
        assert event_publisher.events[0].subject == str(campaign.id)

    asyncio.run(run_case())


def test_marketing_campaign_sqlalchemy_row_maps_domain_model() -> None:
    campaign = asyncio.run(
        _create_campaign(
            name="Mapping Test",
            audience_user_ids=["user-1"],
        )
    )

    row = MarketingCampaignRow.from_domain(campaign)
    mapped_campaign = row.to_domain()

    assert mapped_campaign.id == campaign.id
    assert mapped_campaign.name == campaign.name
    assert mapped_campaign.status == CampaignStatusEnum.DRAFT
    assert mapped_campaign.channel == CampaignChannelEnum.EMAIL
    assert mapped_campaign.audience == ["user-1"]


async def _create_campaign(
    *,
    name: str,
    audience_user_ids: list[str],
):
    repository = InMemoryMarketingRepository()
    event_publisher = CapturingEventPublisher()
    service = MarketingService(
        marketing_repository=repository,
        event_publisher=event_publisher,
    )

    return await service.create_campaign(
        CreateCampaignCommand(
            name=name,
            description="Description",
            channel=CampaignChannelEnum.EMAIL,
            audience_segments=[],
            audience_user_ids=audience_user_ids,
            content_template="Hello",
            start_date=date(2026, 6, 1),
            frequency=ScheduleFrequencyEnum.ONE_TIME,
        )
    )
