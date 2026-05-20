from dataclasses import dataclass
from datetime import date

from luxtj.domain.enums import CampaignChannelEnum, ScheduleFrequencyEnum


@dataclass
class CreateCampaignDTO:
    name: str
    description: str
    channel: CampaignChannelEnum
    audience_segments: list[str]
    audience_user_ids: list[str]
    content_template: str
    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None = None


@dataclass
class UpdateCampaignDTO:
    name: str
    description: str
    channel: CampaignChannelEnum
    audience_user_ids: list[str]
    content_template: str
    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None = None
