from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    OfferStatusEnum,
    OfferTypeEnum,
    ScheduleFrequencyEnum,
)
from luxtj.contexts.marketing.domain.offer import Offer
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel
from luxtj.utils import mockutils


class CampaignAudienceBody(ApiSerializerBaseModel):
    segments: list[str] = Field(
        default_factory=list,
        description="List of audience segments to target.",
    )
    specific_users: list[str] = Field(
        default_factory=list,
        description="List of specific user identifiers to target.",
    )


class CampaignContentBody(ApiSerializerBaseModel):
    template: str = Field(..., description="Content template with placeholders for personalization")


class CampaignScheduleBody(ApiSerializerBaseModel):
    start_date: date = Field(..., description="Campaign start date")
    frequency: ScheduleFrequencyEnum = Field(..., description="Campaign schedule frequency")
    frequency_schedule: str | None = Field(
        None,
        description="Cron expression or natural language description for recurring schedules.",
    )


class CreateCampaignBody(ApiSerializerBaseModel):
    campaign_name: str = Field(..., description="Campaign name")
    description: str = Field("", description="Campaign description")
    channel: CampaignChannelEnum = Field(..., description="Campaign channel")
    audience: CampaignAudienceBody
    content: CampaignContentBody
    schedule: CampaignScheduleBody


class UpdateCampaignBody(ApiSerializerBaseModel):
    campaign_name: str | None = Field(None, description="Campaign name")
    description: str | None = Field(None, description="Campaign description")
    channel: CampaignChannelEnum | None = Field(None, description="Campaign channel")
    audience_user_ids: list[str] | None = Field(
        None, description="List of specific user identifiers to target."
    )
    content_template: str | None = Field(
        None, description="Content template with placeholders for personalization"
    )
    start_date: date | None = Field(None, description="Campaign start date")
    frequency: ScheduleFrequencyEnum | None = Field(None, description="Campaign schedule frequency")
    frequency_schedule: str | None = Field(
        None, description="Cron expression for recurring schedules."
    )
    status: CampaignStatusEnum | None = Field(None, description="Campaign status")


class CampaignSerializer(ApiSerializerBaseModel):
    campaign_id: str
    campaign_name: str
    description: str
    status: CampaignStatusEnum
    channel: CampaignChannelEnum
    audience: list[dict[str, object]]
    content: CampaignContentBody
    schedule: CampaignScheduleBody
    created_at: datetime

    @classmethod
    def from_campaign(cls, campaign: MarketingCampaign) -> CampaignSerializer:
        return cls(
            campaign_id=str(campaign.id),
            campaign_name=campaign.name,
            description=campaign.description,
            status=campaign.status,
            channel=campaign.channel,
            audience=[
                {"userId": item, "userEmail": mockutils.random_user_email()}
                for item in campaign.audience
            ],
            content=CampaignContentBody(template=campaign.content),
            schedule=CampaignScheduleBody(
                start_date=campaign.start_date,
                frequency=campaign.frequency,
                frequency_schedule=campaign.frequency_schedule,
            ),
            created_at=campaign.created_at,
        )


class CreateOfferBody(ApiSerializerBaseModel):
    name: str = Field(..., description="Offer name")
    code: str | None = Field(None, description="Offer code; auto-generated if not provided")
    type: OfferTypeEnum = Field(..., description="Offer type")
    discount_value: float = Field(..., description="Discount value")
    min_booking_value: float = Field(..., description="Minimum booking value to apply offer")
    min_booking_value_currency: str = Field(..., description="Currency code for min booking value")
    validity_start: datetime = Field(..., description="Offer validity start (must be in future)")
    validity_end: datetime = Field(..., description="Offer validity end (must be after start)")
    usage_limit_per_user: int | None = Field(
        None, description="Max uses per user; null = unlimited"
    )
    applicability_on: list[str] = Field(
        default_factory=list, description="Product categories this offer applies to"
    )
    stackable: bool = Field(False, description="Whether offer can stack with others")
    auto_apply: bool = Field(True, description="Whether offer is applied automatically")


class OfferSerializer(ApiSerializerBaseModel):
    offer_id: str
    name: str
    code: str
    type: OfferTypeEnum
    discount_value: float
    min_booking_value: float
    min_booking_value_currency: str
    validity_start: datetime
    validity_end: datetime
    usage_limit_per_user: int | None
    applicability_on: list[str]
    stackable: bool
    auto_apply: bool
    status: OfferStatusEnum
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_offer(cls, offer: Offer) -> OfferSerializer:
        return cls(
            offer_id=str(offer.id),
            name=offer.name,
            code=offer.code,
            type=offer.type,
            discount_value=offer.discount_value,
            min_booking_value=offer.min_booking_value,
            min_booking_value_currency=offer.min_booking_value_currency,
            validity_start=offer.validity_start,
            validity_end=offer.validity_end,
            usage_limit_per_user=offer.usage_limit_per_user,
            applicability_on=offer.applicability_on,
            stackable=offer.stackable,
            auto_apply=offer.auto_apply,
            status=offer.status,
            created_at=offer.created_at,
            updated_at=offer.updated_at,
            deleted_at=offer.deleted_at,
        )
