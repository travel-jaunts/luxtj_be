from typing import Protocol
from uuid import UUID

from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
)
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.enums import OfferStatusEnum, OfferTypeEnum
from luxtj.contexts.marketing.domain.offer import Offer


class MarketingRepository(Protocol):
    async def list(self) -> list[MarketingCampaign]: ...

    async def add(self, campaign: MarketingCampaign) -> MarketingCampaign: ...

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign: ...

    async def save(self, campaign: MarketingCampaign) -> MarketingCampaign: ...

    async def delete(self, campaign_id: str) -> MarketingCampaign: ...


class AudienceResolver(Protocol):
    async def resolve_campaign_audience(self, command: CreateCampaignCommand) -> list[str]: ...


class OfferRepository(Protocol):
    async def add(self, offer: Offer) -> None: ...

    async def get_by_id(self, offer_id: UUID) -> Offer: ...

    async def search(
        self,
        name: str | None,
        status: OfferStatusEnum | None,
        type: OfferTypeEnum | None,
    ) -> list[Offer]: ...

    async def save(self, offer: Offer) -> None: ...
