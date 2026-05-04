from __future__ import annotations

from pydantic import AwareDatetime, Field

from admin_api.reports.marketing.domainmodel import (
    CampaignChannelEnum,
    CampaignPerformanceReportDomainModel,
    CampaignPerformanceRowDomainModel,
    CampaignPerformanceTotalsDomainModel,
    OfferPerformanceReportDomainModel,
    OfferPerformanceRowDomainModel,
    OfferPerformanceTotalsDomainModel,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel
from luxtj.domain.enums import (
    BookingTypeEnum,
    OfferApplicabilityEnum,
    OfferCostBearerEnum,
    OfferStatusEnum,
    OfferTypeEnum,
)


class MarketingNameSearchQuery(ApiSerializerBaseModel):
    name: str | None = Field(None, description="Name text used to filter report rows")


class CampaignPerformanceTotals(ApiSerializerBaseModel):
    impressions: int
    clicks: int
    bookings: int
    spend: AmountSerializer
    revenue: AmountSerializer
    click_through_rate: float
    conversion_rate: float
    return_on_ad_spend: float

    @classmethod
    def from_domain_model(
        cls, domain_model: CampaignPerformanceTotalsDomainModel
    ) -> CampaignPerformanceTotals:
        return cls(
            impressions=domain_model.impressions,
            clicks=domain_model.clicks,
            bookings=domain_model.bookings,
            spend=AmountSerializer(
                amount=domain_model.spend_amount,
                currency=domain_model.currency,
            ),
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.currency,
            ),
            click_through_rate=domain_model.click_through_rate,
            conversion_rate=domain_model.conversion_rate,
            return_on_ad_spend=domain_model.return_on_ad_spend,
        )


class CampaignPerformanceRow(ApiSerializerBaseModel):
    campaign_id: str
    campaign_name: str
    channel: CampaignChannelEnum
    impressions: int
    clicks: int
    bookings: int
    spend: AmountSerializer
    revenue: AmountSerializer
    click_through_rate: float
    conversion_rate: float
    return_on_ad_spend: float

    @classmethod
    def from_domain_model(
        cls, domain_model: CampaignPerformanceRowDomainModel
    ) -> CampaignPerformanceRow:
        return cls(
            campaign_id=domain_model.campaign_id,
            campaign_name=domain_model.campaign_name,
            channel=domain_model.channel,
            impressions=domain_model.impressions,
            clicks=domain_model.clicks,
            bookings=domain_model.bookings,
            spend=AmountSerializer(
                amount=domain_model.spend_amount,
                currency=domain_model.currency,
            ),
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.currency,
            ),
            click_through_rate=domain_model.click_through_rate,
            conversion_rate=domain_model.conversion_rate,
            return_on_ad_spend=domain_model.return_on_ad_spend,
        )


class CampaignPerformanceReport(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    currency: str
    totals: CampaignPerformanceTotals
    rows: list[CampaignPerformanceRow]

    @classmethod
    def from_domain_model(
        cls, domain_model: CampaignPerformanceReportDomainModel
    ) -> CampaignPerformanceReport:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            totals=CampaignPerformanceTotals.from_domain_model(domain_model.totals),
            rows=[CampaignPerformanceRow.from_domain_model(row) for row in domain_model.rows],
        )


class OfferPerformanceTotals(ApiSerializerBaseModel):
    usage_count: int
    booking_count: int
    total_discount_given: AmountSerializer
    revenue_after_discount: AmountSerializer
    average_discount_per_booking: AmountSerializer

    @classmethod
    def from_domain_model(
        cls, domain_model: OfferPerformanceTotalsDomainModel
    ) -> OfferPerformanceTotals:
        return cls(
            usage_count=domain_model.usage_count,
            booking_count=domain_model.booking_count,
            total_discount_given=AmountSerializer(
                amount=domain_model.total_discount_given,
                currency=domain_model.currency,
            ),
            revenue_after_discount=AmountSerializer(
                amount=domain_model.revenue_after_discount,
                currency=domain_model.currency,
            ),
            average_discount_per_booking=AmountSerializer(
                amount=domain_model.average_discount_per_booking,
                currency=domain_model.currency,
            ),
        )


class OfferPerformanceRow(ApiSerializerBaseModel):
    offer_id: str
    title: str
    offer_type: OfferTypeEnum
    offer_value: float
    offer_currency: str
    offer_on: BookingTypeEnum
    applicable_on: OfferApplicabilityEnum
    min_booking_amount: AmountSerializer
    max_discount_cap: float
    per_user_limit: int
    stackable: bool
    usage_count: int
    total_discount_given: AmountSerializer
    cost_bearer: OfferCostBearerEnum
    validity_from: AwareDatetime
    validity_to: AwareDatetime
    offer_status: OfferStatusEnum
    revenue_after_discount: AmountSerializer
    booking_count: int
    average_discount_per_booking: AmountSerializer

    @classmethod
    def from_domain_model(cls, domain_model: OfferPerformanceRowDomainModel) -> OfferPerformanceRow:
        return cls(
            offer_id=domain_model.offer_id,
            title=domain_model.title,
            offer_type=domain_model.offer_type,
            offer_value=domain_model.offer_value,
            offer_currency=domain_model.offer_currency,
            offer_on=domain_model.offer_on,
            applicable_on=domain_model.applicable_on,
            min_booking_amount=AmountSerializer(
                amount=domain_model.min_booking_amount,
                currency=domain_model.offer_currency,
            ),
            max_discount_cap=domain_model.max_discount_cap,
            per_user_limit=domain_model.per_user_limit,
            stackable=domain_model.stackable,
            usage_count=domain_model.usage_count,
            total_discount_given=AmountSerializer(
                amount=domain_model.total_discount_given,
                currency=domain_model.offer_currency,
            ),
            cost_bearer=domain_model.cost_bearer,
            validity_from=domain_model.validity_from,
            validity_to=domain_model.validity_to,
            offer_status=domain_model.offer_status,
            revenue_after_discount=AmountSerializer(
                amount=domain_model.revenue_after_discount,
                currency=domain_model.offer_currency,
            ),
            booking_count=domain_model.booking_count,
            average_discount_per_booking=AmountSerializer(
                amount=domain_model.average_discount_per_booking,
                currency=domain_model.offer_currency,
            ),
        )


class OfferPerformanceReport(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    currency: str
    totals: OfferPerformanceTotals
    rows: list[OfferPerformanceRow]

    @classmethod
    def from_domain_model(
        cls, domain_model: OfferPerformanceReportDomainModel
    ) -> OfferPerformanceReport:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            totals=OfferPerformanceTotals.from_domain_model(domain_model.totals),
            rows=[OfferPerformanceRow.from_domain_model(row) for row in domain_model.rows],
        )
