from typing import Any

from pydantic import Field

from luxtj.domain.event.base import BaseDomainEvent
from luxtj.domain.model import MarketingCampaign


class DEMarketingCampaignCreated(BaseDomainEvent):
    source: str = "/luxtj/marketing/campaigns"
    type: str = "com.luxtj.marketing.campaign.created"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(
        default=None, description="Created marketing campaign payload."
    )

    @classmethod
    def from_campaign(cls, campaign: MarketingCampaign) -> DEMarketingCampaignCreated:
        return cls(
            subject=str(campaign.id),
            data={
                "id": str(campaign.id),
                "name": campaign.name,
                "description": campaign.description,
                "channel": campaign.channel,
                "audience": campaign.audience,
                "content": campaign.content,
                "start_date": campaign.start_date.isoformat(),
                "frequency": campaign.frequency,
                "created_at": campaign.created_at.isoformat(),
            },
        )
