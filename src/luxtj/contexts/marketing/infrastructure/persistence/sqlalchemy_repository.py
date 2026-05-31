from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.enums import OfferStatusEnum, OfferTypeEnum
from luxtj.contexts.marketing.domain.offer import Offer
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import (
    MarketingCampaignRow,
    MarketingOfferRow,
)
from luxtj.utils import timeutils


class SqlAlchemyMarketingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> list[MarketingCampaign]:
        rows = await self.session.scalars(
            select(MarketingCampaignRow)
            .where(MarketingCampaignRow.deleted_at.is_(None))
            .order_by(MarketingCampaignRow.created_at.desc())
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

        now = timeutils.datetime_now()
        row.deleted_at = now
        row.updated_at = now
        return row.to_domain()


class SqlAlchemyOfferRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, offer: Offer) -> None:
        self.session.add(MarketingOfferRow.from_domain(offer))

    async def get_by_id(self, offer_id: UUID) -> Offer:
        row = await self.session.get(MarketingOfferRow, str(offer_id))
        if row is None:
            raise KeyError(str(offer_id))
        return row.to_domain()

    async def search(
        self,
        name: str | None,
        status: OfferStatusEnum | None,
        type: OfferTypeEnum | None,
    ) -> list[Offer]:
        query = select(MarketingOfferRow).where(
            MarketingOfferRow.status != OfferStatusEnum.DELETED.value
        )
        if name is not None:
            query = query.where(MarketingOfferRow.name.ilike(f"%{name}%"))
        if status is not None:
            query = query.where(MarketingOfferRow.status == status.value)
        if type is not None:
            query = query.where(MarketingOfferRow.type == type.value)
        query = query.order_by(MarketingOfferRow.created_at.desc())
        rows = await self.session.scalars(query)
        return [row.to_domain() for row in rows]

    async def save(self, offer: Offer) -> None:
        row = await self.session.get(MarketingOfferRow, str(offer.id))
        if row is None:
            raise KeyError(str(offer.id))
        row.update_from_domain(offer)
