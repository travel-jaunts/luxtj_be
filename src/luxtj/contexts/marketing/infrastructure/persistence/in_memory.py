from luxtj.contexts.marketing.application.commands import CreateCampaignCommand
from luxtj.contexts.marketing.application.ports import IMarketingRepository
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.utils import mockutils


class InMemoryMarketingRepository(IMarketingRepository):
    def __init__(self) -> None:
        self._campaigns: dict[str, MarketingCampaign] = {}

    async def list(self) -> list[MarketingCampaign]:
        return list(self._campaigns.values())

    async def add(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[str(campaign.id)] = campaign
        return campaign

    async def get_by_id(self, campaign_id: str) -> MarketingCampaign:
        return self._campaigns[campaign_id]

    async def save(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[str(campaign.id)] = campaign
        return campaign

    async def delete(self, campaign_id: str) -> MarketingCampaign:
        return self._campaigns.pop(campaign_id)


class MockMarketingAudienceResolver:
    async def resolve_campaign_audience(self, command: CreateCampaignCommand) -> list[str]:
        if command.audience_user_ids:
            return list(command.audience_user_ids)

        return mockutils.random_user_ids(2, 10)
