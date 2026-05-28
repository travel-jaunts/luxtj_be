from typing import Protocol

from luxtj.contexts.marketing.application.commands import (
    CreateCampaignCommand,
)
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign


class IMarketingRepository(Protocol):
    async def list(self) -> list[MarketingCampaign]: ...

    async def add(self, campaign: MarketingCampaign) -> MarketingCampaign: ...

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign: ...

    async def save(self, campaign: MarketingCampaign) -> MarketingCampaign: ...

    async def delete(self, campaign_id: str) -> MarketingCampaign: ...


class AudienceResolver(Protocol):
    async def resolve_campaign_audience(self, command: CreateCampaignCommand) -> list[str]: ...
