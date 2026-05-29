from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from uuid import UUID, uuid7

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
    deleted_at: datetime | None = None
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

    @classmethod
    def duplicate(cls, source: MarketingCampaign) -> MarketingCampaign:
        from luxtj.contexts.marketing.domain.events import MarketingCampaignDuplicated

        new_start_date = date.today() + timedelta(days=2)
        now = timeutils.datetime_now()
        
        campaign_creation_policies.enforce_all(
            CampaignCreationContext(
                start_date=new_start_date,
                frequency=source.frequency,
                frequency_schedule=source.frequency_schedule,
            )
        )
        
        duplicate_campaign = cls(
            id=uuid7(),
            name=source.name,
            description=source.description,
            status=CampaignStatusEnum.DRAFT,
            channel=source.channel,
            audience=list(source.audience),
            content=source.content,
            start_date=new_start_date,
            frequency=source.frequency,
            frequency_schedule=source.frequency_schedule,
            created_at=now,
            updated_at=now,
        )

        duplicate_campaign.record_event(MarketingCampaignDuplicated.from_campaigns(source, duplicate_campaign))
        return duplicate_campaign

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
        from luxtj.contexts.marketing.domain.events import MarketingCampaignUpdated

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
        
        self.record_event(MarketingCampaignUpdated.from_campaign(self))
        
    def delete(self) -> None:
        from luxtj.contexts.marketing.domain.events import MarketingCampaignDeleted
        self.record_event(MarketingCampaignDeleted.from_campaign(self))

    def pause(self) -> None:
        from luxtj.contexts.marketing.domain.events import MarketingCampaignPaused
        self.status = CampaignStatusEnum.PAUSED
        self.updated_at = timeutils.datetime_now()
        self.record_event(MarketingCampaignPaused.from_campaign(self))

    def record_event(self, event: BaseDomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[BaseDomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
