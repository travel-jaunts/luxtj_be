from typing import Protocol

from luxtj.application.dto.marketing import CreateCampaignDTO, UpdateCampaignDTO
from luxtj.domain.model import MarketingCampaign


class IMarketingRepository(Protocol):
    async def list(self) -> list[MarketingCampaign]: ...

    async def create(self, campaign_data: CreateCampaignDTO) -> MarketingCampaign: ...

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign: ...

    async def update(
        self, campaign_id: str, update_data: UpdateCampaignDTO
    ) -> MarketingCampaign: ...

    async def delete(self, campaign_id: str) -> MarketingCampaign: ...
