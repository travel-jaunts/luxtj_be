from dataclasses import dataclass
from datetime import date

from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)


@dataclass(frozen=True)
class CreateCampaignCommand:
    name: str
    description: str
    channel: CampaignChannelEnum
    audience_segments: list[str]
    audience_user_ids: list[str]
    content_template: str
    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None = None


@dataclass(frozen=True)
class UpdateCampaignCommand:
    id: str
    name: str | None = None
    description: str | None = None
    channel: CampaignChannelEnum | None = None
    audience_user_ids: list[str] | None = None
    content_template: str | None = None
    start_date: date | None = None
    frequency: ScheduleFrequencyEnum | None = None
    frequency_schedule: str | None = None
    status: CampaignStatusEnum | None = None
