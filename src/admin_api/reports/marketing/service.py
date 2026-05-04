from __future__ import annotations

from admin_api.customer.offers.domainmodel import OfferDomainModel
from admin_api.reports.marketing.domainmodel import (
    CampaignChannelEnum,
    CampaignPerformanceReportDomainModel,
    OfferPerformanceReportDomainModel,
    OfferPerformanceRowDomainModel,
    mock_campaign_row,
)
from luxtj.utils import mockutils

CAMPAIGN_OPTIONS = [
    ("CMP-001", "Summer Escapes", CampaignChannelEnum.EMAIL),
    ("CMP-002", "Festive Luxury", CampaignChannelEnum.SOCIAL),
    ("CMP-003", "Weekend Retreats", CampaignChannelEnum.SEARCH),
    ("CMP-004", "Partner Getaways", CampaignChannelEnum.AFFILIATE),
    ("CMP-005", "Last Minute Deals", CampaignChannelEnum.PUSH),
]

OFFER_OPTIONS = [OfferDomainModel.generate_mock() for _ in range(10)]


class MarketingReportService:
    async def get_campaign_performance(
        self,
        *,
        name: str | None = None,
        iso_currency_str: str,
    ) -> CampaignPerformanceReportDomainModel:
        campaigns = self._filter_campaigns_by_name(name)
        rows = [
            mock_campaign_row(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                channel=channel,
                currency=iso_currency_str,
            )
            for campaign_id, campaign_name, channel in campaigns
        ]
        return CampaignPerformanceReportDomainModel.from_rows(
            currency=iso_currency_str,
            rows=rows,
        )

    async def get_offer_performance(
        self,
        *,
        name: str | None = None,
        iso_currency_str: str,
    ) -> OfferPerformanceReportDomainModel:
        offers = self._filter_offers_by_name(name)
        rows = [
            OfferPerformanceRowDomainModel.from_offer_model(
                offer=self._offer_with_currency(offer, iso_currency_str),
                revenue_after_discount=mockutils.random_booking_amount(50_000.0, 2_500_000.0),
                booking_count=mockutils.random.randint(1, 500),
            )
            for offer in offers
        ]
        return OfferPerformanceReportDomainModel.from_rows(
            currency=iso_currency_str,
            rows=rows,
        )

    def _filter_campaigns_by_name(
        self, name: str | None
    ) -> list[tuple[str, str, CampaignChannelEnum]]:
        normalized_name = (name or "").strip().lower()
        if not normalized_name:
            return CAMPAIGN_OPTIONS

        return [campaign for campaign in CAMPAIGN_OPTIONS if normalized_name in campaign[1].lower()]

    def _filter_offers_by_name(self, name: str | None) -> list[OfferDomainModel]:
        normalized_name = (name or "").strip().lower()
        if not normalized_name:
            return OFFER_OPTIONS

        return [offer for offer in OFFER_OPTIONS if normalized_name in offer.title.lower()]

    def _offer_with_currency(self, offer: OfferDomainModel, currency: str) -> OfferDomainModel:
        offer.offer_currency = currency
        return offer
