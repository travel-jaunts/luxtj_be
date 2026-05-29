from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)
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
