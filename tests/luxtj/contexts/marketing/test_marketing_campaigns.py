"""Marketing campaign application and infrastructure tests."""

import pytest

from luxtj.contexts.marketing.application.commands import UpdateCampaignCommand
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)
from luxtj.contexts.marketing.infrastructure.persistence.in_memory import (
    InMemoryMarketingRepository,
)
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import (
    MarketingCampaignRow,
)
from tests.conftest import CapturingEventPublisher

# ---------------------------------------------------------------------------
# Application layer — MarketingService
# ---------------------------------------------------------------------------


async def test_create_campaign_persists_and_returns_scheduled(
    marketing_service: MarketingService,
    marketing_repo: InMemoryMarketingRepository,
    make_campaign_command,
) -> None:
    campaign = await marketing_service.create_campaign(
        make_campaign_command(name="Summer Escapes", audience_user_ids=["user-1", "user-2"])
    )

    assert campaign.status == CampaignStatusEnum.SCHEDULED
    assert campaign.audience == ["user-1", "user-2"]
    assert await marketing_repo.get_by_id(str(campaign.id)) is campaign


async def test_create_campaign_publishes_created_event(
    marketing_service: MarketingService,
    event_publisher: CapturingEventPublisher,
    make_campaign_command,
) -> None:
    campaign = await marketing_service.create_campaign(make_campaign_command(name="Summer Escapes"))

    created_events = event_publisher.of_type("com.luxtj.marketing.campaign.created.v1")
    assert len(created_events) == 1
    assert created_events[0].subject == str(campaign.id)


async def test_list_campaigns_returns_all_created(
    marketing_service: MarketingService,
    make_campaign_command,
) -> None:
    await marketing_service.create_campaign(make_campaign_command(name="Alpha"))
    await marketing_service.create_campaign(make_campaign_command(name="Beta"))

    campaigns = await marketing_service.list_campaigns()

    assert len(campaigns) == 2
    assert {c.name for c in campaigns} == {"Alpha", "Beta"}


async def test_update_campaign_applies_changes(
    marketing_service: MarketingService,
    make_campaign_command,
) -> None:
    from datetime import date

    original = await marketing_service.create_campaign(make_campaign_command(name="Original"))

    updated = await marketing_service.update_campaign(
        UpdateCampaignCommand(
            str(original.id),
            name="Updated",
            description="New description",
            channel=CampaignChannelEnum.SMS,
            audience_user_ids=["user-3"],
            content_template="Hi",
            start_date=date(2026, 7, 1),
            frequency=ScheduleFrequencyEnum.ONE_TIME,
        ),
    )

    assert updated.name == "Updated"
    assert updated.channel == CampaignChannelEnum.SMS
    assert updated.audience == ["user-3"]


async def test_delete_campaign_removes_from_repository(
    marketing_service: MarketingService,
    marketing_repo: InMemoryMarketingRepository,
    make_campaign_command,
) -> None:
    campaign = await marketing_service.create_campaign(make_campaign_command())
    deleted = await marketing_service.delete_campaign(str(campaign.id))

    assert deleted.id == campaign.id
    assert await marketing_repo.list() == []


@pytest.mark.parametrize(
    "audience_ids,expected_count",
    [
        (["user-1"], 1),
        (["user-1", "user-2", "user-3"], 3),
        (["user-1", "user-1", "user-2"], 2),  # duplicates are collapsed
    ],
    ids=["single", "multiple", "deduplication"],
)
async def test_create_campaign_deduplicates_audience(
    marketing_service: MarketingService,
    make_campaign_command,
    audience_ids: list[str],
    expected_count: int,
) -> None:
    campaign = await marketing_service.create_campaign(
        make_campaign_command(audience_user_ids=audience_ids)
    )

    assert len(campaign.audience) == expected_count


# ---------------------------------------------------------------------------
# Infrastructure layer — MarketingCampaignRow ORM mapping
# ---------------------------------------------------------------------------


async def test_campaign_row_round_trip_preserves_all_fields(
    marketing_service: MarketingService,
    make_campaign_command,
) -> None:
    original = await marketing_service.create_campaign(
        make_campaign_command(name="Mapping Test", audience_user_ids=["user-1"])
    )

    row = MarketingCampaignRow.from_domain(original)
    restored = row.to_domain()

    assert restored.id == original.id
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.status == CampaignStatusEnum.SCHEDULED
    assert restored.channel == CampaignChannelEnum.EMAIL
    assert restored.audience == ["user-1"]
    assert restored.start_date == original.start_date
    assert restored.frequency == original.frequency


@pytest.mark.parametrize(
    "channel",
    list(CampaignChannelEnum),
    ids=[c.value for c in CampaignChannelEnum],
)
async def test_campaign_row_round_trip_for_all_channels(
    marketing_service: MarketingService,
    make_campaign_command,
    channel: CampaignChannelEnum,
) -> None:
    original = await marketing_service.create_campaign(
        make_campaign_command(name=f"Channel-{channel}", channel=channel)
    )

    row = MarketingCampaignRow.from_domain(original)
    restored = row.to_domain()

    assert restored.channel == channel
