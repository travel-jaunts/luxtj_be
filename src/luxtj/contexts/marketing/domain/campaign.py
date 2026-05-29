from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)
from luxtj.contexts.marketing.domain.policies import (
    CampaignCreationContext,
    campaign_creation_policies,
)
from luxtj.shared_kernel.domain import BaseDomainEvent
from luxtj.utils import timeutils

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

        now = timeutils.datetime_now()
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
        name: str | None = None,
        description: str | None = None,
        channel: CampaignChannelEnum | None = None,
        audience: Sequence[str] | None = None,
        content: str | None = None,
        start_date: date | None = None,
        frequency: ScheduleFrequencyEnum | None = None,
        frequency_schedule: str | None = None,
        status: CampaignStatusEnum | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if channel is not None:
            self.channel = channel
        if audience is not None:
            self.audience = list(dict.fromkeys(audience))
        if content is not None:
            self.content = content
        if start_date is not None:
            self.start_date = start_date
        if frequency is not None:
            self.frequency = frequency
        if frequency_schedule is not None:
            self.frequency_schedule = frequency_schedule
        if status is not None:
            self.status = status
        self.updated_at = timeutils.datetime_now()

    def record_event(self, event: BaseDomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[BaseDomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
