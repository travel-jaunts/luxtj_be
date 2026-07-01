from datetime import date

import pytest

from luxtj.contexts.marketing.application.commands import CreateCampaignCommand
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.domain.enums import CampaignChannelEnum, ScheduleFrequencyEnum
from luxtj.contexts.marketing.infrastructure.persistence.in_memory import (
    InMemoryMarketingRepository,
)


@pytest.fixture
def marketing_repo() -> InMemoryMarketingRepository:
    return InMemoryMarketingRepository()


@pytest.fixture
def marketing_service(marketing_repo, event_publisher) -> MarketingService:
    return MarketingService(
        marketing_repository=marketing_repo,
        event_publisher=event_publisher,
    )


@pytest.fixture
def make_campaign_command():
    """Factory fixture — call it with keyword overrides to build a CreateCampaignCommand."""

    def _factory(
        *,
        name: str = "Test Campaign",
        description: str = "A test campaign",
        channel: CampaignChannelEnum = CampaignChannelEnum.EMAIL,
        audience_segments: list[str] | None = None,
        audience_user_ids: list[str] | None = None,
        content_template: str = "Hello {{ first_name }}",
        start_date: date | None = None,
        frequency: ScheduleFrequencyEnum = ScheduleFrequencyEnum.ONE_TIME,
        frequency_schedule: str | None = None,
    ) -> CreateCampaignCommand:
        resolved_start_date = start_date or date.today()
        return CreateCampaignCommand(
            name=name,
            description=description,
            channel=channel,
            audience_segments=audience_segments or [],
            audience_user_ids=audience_user_ids or [],
            content_template=content_template,
            start_date=resolved_start_date,
            frequency=frequency,
            frequency_schedule=frequency_schedule,
        )

    return _factory
