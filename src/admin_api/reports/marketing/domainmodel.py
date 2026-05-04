from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from admin_api.customer.offers.domainmodel import OfferDomainModel
from luxtj.domain.enums import (
    BookingTypeEnum,
    OfferApplicabilityEnum,
    OfferCostBearerEnum,
    OfferStatusEnum,
    OfferTypeEnum,
)
from luxtj.utils import mockutils


class CampaignChannelEnum(StrEnum):
    EMAIL = "email"
    SOCIAL = "social"
    SEARCH = "search"
    AFFILIATE = "affiliate"
    PUSH = "push"


@dataclass
class CampaignPerformanceRowDomainModel:
    campaign_id: str
    campaign_name: str
    channel: CampaignChannelEnum
    impressions: int
    clicks: int
    bookings: int
    spend_amount: float
    revenue_amount: float
    currency: str

    @property
    def click_through_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)

    @property
    def conversion_rate(self) -> float:
        if self.clicks == 0:
            return 0.0
        return round((self.bookings / self.clicks) * 100, 2)

    @property
    def return_on_ad_spend(self) -> float:
        if self.spend_amount == 0:
            return 0.0
        return round(self.revenue_amount / self.spend_amount, 2)


@dataclass
class CampaignPerformanceTotalsDomainModel:
    impressions: int
    clicks: int
    bookings: int
    spend_amount: float
    revenue_amount: float
    currency: str

    @property
    def click_through_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)

    @property
    def conversion_rate(self) -> float:
        if self.clicks == 0:
            return 0.0
        return round((self.bookings / self.clicks) * 100, 2)

    @property
    def return_on_ad_spend(self) -> float:
        if self.spend_amount == 0:
            return 0.0
        return round(self.revenue_amount / self.spend_amount, 2)


@dataclass
class CampaignPerformanceReportDomainModel:
    title: str
    generated_at: datetime
    currency: str
    totals: CampaignPerformanceTotalsDomainModel
    rows: list[CampaignPerformanceRowDomainModel]

    @classmethod
    def from_rows(
        cls,
        *,
        currency: str,
        rows: list[CampaignPerformanceRowDomainModel],
    ) -> CampaignPerformanceReportDomainModel:
        return cls(
            title="Campaign Performance",
            generated_at=datetime.now(tz=UTC),
            currency=currency,
            totals=CampaignPerformanceTotalsDomainModel(
                impressions=sum(row.impressions for row in rows),
                clicks=sum(row.clicks for row in rows),
                bookings=sum(row.bookings for row in rows),
                spend_amount=round(sum(row.spend_amount for row in rows), 2),
                revenue_amount=round(sum(row.revenue_amount for row in rows), 2),
                currency=currency,
            ),
            rows=rows,
        )


@dataclass
class OfferPerformanceRowDomainModel:
    offer_id: str
    title: str
    offer_type: OfferTypeEnum
    offer_value: float
    offer_currency: str
    offer_on: BookingTypeEnum
    applicable_on: OfferApplicabilityEnum
    min_booking_amount: float
    max_discount_cap: float
    per_user_limit: int
    stackable: bool
    usage_count: int
    total_discount_given: float
    cost_bearer: OfferCostBearerEnum
    validity_from: datetime
    validity_to: datetime
    offer_status: OfferStatusEnum
    revenue_after_discount: float
    booking_count: int

    @classmethod
    def from_offer_model(
        cls,
        *,
        offer: OfferDomainModel,
        revenue_after_discount: float,
        booking_count: int,
    ) -> OfferPerformanceRowDomainModel:
        return cls(
            offer_id=offer.offer_id,
            title=offer.title,
            offer_type=offer.offer_type,
            offer_value=offer.offer_value,
            offer_currency=offer.offer_currency,
            offer_on=offer.offer_on,
            applicable_on=offer.applicable_on,
            min_booking_amount=offer.min_booking_amount,
            max_discount_cap=offer.max_discount_cap,
            per_user_limit=offer.per_user_limit,
            stackable=offer.stackable,
            usage_count=offer.usage_count,
            total_discount_given=offer.total_discount_given,
            cost_bearer=offer.cost_bearer,
            validity_from=offer.validity_from,
            validity_to=offer.validity_to,
            offer_status=offer.offer_status,
            revenue_after_discount=revenue_after_discount,
            booking_count=booking_count,
        )

    @property
    def average_discount_per_booking(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.total_discount_given / self.booking_count, 2)


@dataclass
class OfferPerformanceTotalsDomainModel:
    usage_count: int
    booking_count: int
    total_discount_given: float
    revenue_after_discount: float
    currency: str

    @property
    def average_discount_per_booking(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.total_discount_given / self.booking_count, 2)


@dataclass
class OfferPerformanceReportDomainModel:
    title: str
    generated_at: datetime
    currency: str
    totals: OfferPerformanceTotalsDomainModel
    rows: list[OfferPerformanceRowDomainModel]

    @classmethod
    def from_rows(
        cls,
        *,
        currency: str,
        rows: list[OfferPerformanceRowDomainModel],
    ) -> OfferPerformanceReportDomainModel:
        return cls(
            title="Offer Performance",
            generated_at=datetime.now(tz=UTC),
            currency=currency,
            totals=OfferPerformanceTotalsDomainModel(
                usage_count=sum(row.usage_count for row in rows),
                booking_count=sum(row.booking_count for row in rows),
                total_discount_given=round(sum(row.total_discount_given for row in rows), 2),
                revenue_after_discount=round(sum(row.revenue_after_discount for row in rows), 2),
                currency=currency,
            ),
            rows=rows,
        )


def mock_campaign_row(
    *,
    campaign_id: str,
    campaign_name: str,
    channel: CampaignChannelEnum,
    currency: str,
) -> CampaignPerformanceRowDomainModel:
    impressions = mockutils.random.randint(5_000, 500_000)
    clicks = mockutils.random.randint(250, max(250, impressions // 6))
    bookings = mockutils.random.randint(5, max(5, clicks // 10))
    spend_amount = mockutils.random_booking_amount(25_000.0, 900_000.0)
    revenue_amount = mockutils.random_booking_amount(spend_amount, spend_amount * 8)
    return CampaignPerformanceRowDomainModel(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        channel=channel,
        impressions=impressions,
        clicks=clicks,
        bookings=bookings,
        spend_amount=spend_amount,
        revenue_amount=revenue_amount,
        currency=currency,
    )
