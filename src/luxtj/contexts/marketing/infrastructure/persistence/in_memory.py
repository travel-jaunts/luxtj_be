from luxtj.contexts.marketing.application.commands import CreateCampaignCommand
from luxtj.contexts.marketing.application.ports import MarketingRepository
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.utils import mockutils, timeutils


class InMemoryMarketingRepository(MarketingRepository):
    def __init__(self) -> None:
        self._campaigns: dict[str, MarketingCampaign] = {}

    async def list(self) -> list[MarketingCampaign]:
        return [c for c in self._campaigns.values() if c.deleted_at is None]

    async def add(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[str(campaign.id)] = campaign
        return campaign

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign:
        return self._campaigns[campaign_id]

    async def save(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[str(campaign.id)] = campaign
        return campaign

    async def delete(self, campaign_id: str) -> MarketingCampaign:
        campaign = self._campaigns[campaign_id]
        now = timeutils.datetime_now()
        campaign.deleted_at = now
        campaign.updated_at = now
        return campaign


class MockMarketingAudienceResolver:
    async def resolve_campaign_audience(self, command: CreateCampaignCommand) -> list[str]:
        if command.audience_user_ids:
            return list(command.audience_user_ids)

        return mockutils.random_user_ids(2, 10)
