from dataclasses import dataclass
from datetime import date

from luxtj.contexts.marketing.domain.enums import CampaignChannelEnum, ScheduleFrequencyEnum


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
    name: str
    description: str
    channel: CampaignChannelEnum
    audience_user_ids: list[str]
    content_template: str
    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None = None
