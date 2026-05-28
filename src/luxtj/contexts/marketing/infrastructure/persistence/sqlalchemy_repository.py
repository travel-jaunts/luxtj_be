from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import (
    MarketingCampaignRow,
)


class SqlAlchemyMarketingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> list[MarketingCampaign]:
        rows = await self.session.scalars(
            select(MarketingCampaignRow).order_by(MarketingCampaignRow.created_at.desc())
        )
        return [row.to_domain() for row in rows]

    async def add(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self.session.add(MarketingCampaignRow.from_domain(campaign))
        return campaign

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign:
        row = await self.session.get(MarketingCampaignRow, campaign_id)
        if row is None:
            raise KeyError(campaign_id)
        return row.to_domain()

    async def save(self, campaign: MarketingCampaign) -> MarketingCampaign:
        row = await self.session.get(MarketingCampaignRow, str(campaign.id))
        if row is None:
            raise KeyError(str(campaign.id))

        row.update_from_domain(campaign)
        return campaign

    async def delete(self, campaign_id: str) -> MarketingCampaign:
        row = await self.session.get(MarketingCampaignRow, campaign_id)
        if row is None:
            raise KeyError(campaign_id)

        campaign = row.to_domain()
        await self.session.delete(row)
        return campaign
