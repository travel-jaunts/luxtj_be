from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    OfferStatusEnum,
    OfferTypeEnum,
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
class DuplicateCampaignCommand:
    id: str


@dataclass(frozen=True)
class PauseCampaignCommand:
    id: str


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


@dataclass(frozen=True)
class CreateOfferCommand:
    name: str
    type: OfferTypeEnum
    discount_value: float
    min_booking_value: float
    min_booking_value_currency: str
    validity_start: datetime
    validity_end: datetime
    applicability_on: list[str]
    code: str | None = None
    usage_limit_per_user: int | None = None
    stackable: bool = False
    auto_apply: bool = True


@dataclass(frozen=True)
class SearchOffersCommand:
    name: str | None = None
    status: OfferStatusEnum | None = None
    type: OfferTypeEnum | None = None


@dataclass(frozen=True)
class PauseOfferCommand:
    offer_id: UUID


@dataclass(frozen=True)
class RescindOfferCommand:
    offer_id: UUID


@dataclass(frozen=True)
class DeleteOfferCommand:
    offer_id: UUID
