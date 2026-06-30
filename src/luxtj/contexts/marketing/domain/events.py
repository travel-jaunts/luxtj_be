from typing import Any

from pydantic import Field

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.offer import Offer
from luxtj.shared_kernel.domain.events import BaseDomainEvent


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


class MarketingCampaignDuplicated(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/campaign"
    type: str = "com.luxtj.marketing.campaign.duplicated.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(
        default=None,
        description="Duplicated marketing campaign payload.",
    )

    @classmethod
    def from_campaigns(
        cls, source: MarketingCampaign, duplicate: MarketingCampaign
    ) -> MarketingCampaignDuplicated:
        return cls(
            subject=str(duplicate.id),
            time=duplicate.created_at,
            data={
                "id": str(duplicate.id),
                "source_id": str(source.id),
                "name": duplicate.name,
                "description": duplicate.description,
                "status": duplicate.status.value,
                "channel": duplicate.channel.value,
                # "audience": list(duplicate.audience),
                # "content": duplicate.content,
                "start_date": duplicate.start_date.isoformat(),
                "frequency": duplicate.frequency.value,
                "frequency_schedule": duplicate.frequency_schedule,
                "created_at": duplicate.created_at.isoformat(),
            },
        )


class MarketingCampaignUpdated(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/campaign"
    type: str = "com.luxtj.marketing.campaign.updated.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(
        default=None,
        description="Updated marketing campaign payload.",
    )

    @classmethod
    def from_campaign(cls, campaign: MarketingCampaign) -> MarketingCampaignUpdated:
        return cls(
            subject=str(campaign.id),
            time=campaign.updated_at,
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
                "updated_at": campaign.updated_at.isoformat(),
            },
        )


class MarketingCampaignDeleted(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/campaign"
    type: str = "com.luxtj.marketing.campaign.deleted.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(
        default=None,
        description="Deleted marketing campaign payload.",
    )

    @classmethod
    def from_campaign(cls, campaign: MarketingCampaign) -> MarketingCampaignDeleted:
        return cls(
            subject=str(campaign.id),
            time=campaign.deleted_at,
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
                "deleted_at": campaign.deleted_at.isoformat(),
            },
        )


class MarketingCampaignPaused(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/campaign"
    type: str = "com.luxtj.marketing.campaign.paused.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(
        default=None,
        description="Paused marketing campaign payload.",
    )

    @classmethod
    def from_campaign(cls, campaign: MarketingCampaign) -> MarketingCampaignPaused:
        return cls(
            subject=str(campaign.id),
            time=campaign.updated_at,
            data={
                "id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
                "updated_at": campaign.updated_at.isoformat(),
            },
        )


class OfferCreated(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/offer"
    type: str = "com.luxtj.marketing.offer.created.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_offer(cls, offer: Offer) -> OfferCreated:
        return cls(
            subject=str(offer.id),
            time=offer.created_at,
            data={
                "id": str(offer.id),
                "name": offer.name,
                "code": offer.code,
                "type": offer.type.value,
                "status": offer.status.value,
                "created_at": offer.created_at.isoformat(),
            },
        )


class OfferPaused(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/offer"
    type: str = "com.luxtj.marketing.offer.paused.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_offer(cls, offer: Offer) -> OfferPaused:
        return cls(
            subject=str(offer.id),
            time=offer.updated_at,
            data={
                "id": str(offer.id),
                "name": offer.name,
                "status": offer.status.value,
                "updated_at": offer.updated_at.isoformat(),
            },
        )


class OfferRescinded(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/offer"
    type: str = "com.luxtj.marketing.offer.rescinded.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_offer(cls, offer: Offer) -> OfferRescinded:
        return cls(
            subject=str(offer.id),
            time=offer.updated_at,
            data={
                "id": str(offer.id),
                "name": offer.name,
                "status": offer.status.value,
                "updated_at": offer.updated_at.isoformat(),
            },
        )


class OfferDeleted(BaseDomainEvent):
    source: str = "/luxtj/contexts/marketing/domain/offer"
    type: str = "com.luxtj.marketing.offer.deleted.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_offer(cls, offer: Offer) -> OfferDeleted:
        return cls(
            subject=str(offer.id),
            time=offer.deleted_at,
            data={
                "id": str(offer.id),
                "name": offer.name,
                "status": offer.status.value,
                "deleted_at": offer.deleted_at.isoformat() if offer.deleted_at else None,
            },
        )
