from __future__ import annotations

from typing import Any

from pydantic import Field

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.shared_kernel.domain import BaseDomainEvent


class MarketingCampaignCreated(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/campaign"
    type: str = "com.luxtj.marketing.campaign.created.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(
        default=None,
        description="Created marketing campaign payload.",
    )

    @classmethod
    def from_campaign(cls, campaign: MarketingCampaign) -> MarketingCampaignCreated:
        return cls(
            subject=str(campaign.id),
            time=campaign.created_at,
            data={
                "id": str(campaign.id),
                "name": campaign.name,
                "description": campaign.description,
                "status": campaign.status.value,
                "channel": campaign.channel.value,
                # "audience": list(campaign.audience),
                # "content": campaign.content,
                "start_date": campaign.start_date.isoformat(),
                "frequency": campaign.frequency.value,
                "frequency_schedule": campaign.frequency_schedule,
                "created_at": campaign.created_at.isoformat(),
            },
        )
