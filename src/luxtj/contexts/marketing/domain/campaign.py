from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID

from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)
from luxtj.contexts.marketing.domain.policies import CampaignCreationContext, campaign_creation_policies
from luxtj.shared_kernel.domain import BaseDomainEvent

try:
    from uuid import uuid7
except ImportError:  # pragma: no cover - Python < 3.14 compatibility for local tooling
    from uuid import uuid4 as uuid7


@dataclass
class MarketingCampaign:
    id: UUID
    name: str
    description: str
    status: CampaignStatusEnum
    channel: CampaignChannelEnum
    audience: list[str]
    content: str
    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None
    created_at: datetime
    updated_at: datetime
    _events: list[BaseDomainEvent] = field(
        default_factory=list[BaseDomainEvent], init=False, repr=False
    )

    @classmethod
    def create(
        cls,
        *,
        name: str,
        description: str,
        channel: CampaignChannelEnum,
        audience: Sequence[str],
        content: str,
        start_date: date,
        frequency: ScheduleFrequencyEnum,
        frequency_schedule: str | None,
    ) -> MarketingCampaign:
        from luxtj.contexts.marketing.domain.events import MarketingCampaignCreated

        campaign_creation_policies.enforce_all(
            CampaignCreationContext(
                start_date=start_date,
                frequency=frequency,
                frequency_schedule=frequency_schedule,
            )
        )

        now = datetime.now(UTC)
        campaign = cls(
            id=uuid7(),
            name=name,
            description=description,
            status=CampaignStatusEnum.SCHEDULED,
            channel=channel,
            audience=list(dict.fromkeys(audience)),
            content=content,
            start_date=start_date,
            frequency=frequency,
            frequency_schedule=frequency_schedule,
            created_at=now,
            updated_at=now,
        )
        campaign.record_event(MarketingCampaignCreated.from_campaign(campaign))
        return campaign

    def update(
        self,
        *,
        name: str,
        description: str,
        channel: CampaignChannelEnum,
        audience: Sequence[str],
        content: str,
        start_date: date,
        frequency: ScheduleFrequencyEnum,
        frequency_schedule: str | None,
    ) -> None:
        self.name = name
        self.description = description
        self.channel = channel
        self.audience = list(dict.fromkeys(audience))
        self.content = content
        self.start_date = start_date
        self.frequency = frequency
        self.frequency_schedule = frequency_schedule
        self.updated_at = datetime.now(UTC)

    def record_event(self, event: BaseDomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[BaseDomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
