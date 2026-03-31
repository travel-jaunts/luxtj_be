from pydantic import AwareDatetime

from common.serializerlib import ApiSerializerBaseModel, AmountSerializer
from admin_api.customer.offers.domainmodel import OffersKpiSummaryDomainModel, OfferDomainModel
from luxtj.domain.enums import (
    OfferTypeEnum,
    BookingTypeEnum,
    OfferCostBearerEnum,
    OfferStatusEnum,
    OfferApplicabilityEnum,
)


class OffersKpiSummarySerializer(ApiSerializerBaseModel):
    total_discount_given: AmountSerializer
    discount_percentage_of_revenue: float
    average_discount_per_booking: float
    bookings_with_discount_percentage: float
    net_revenue_after_discount: AmountSerializer

    @classmethod
    def from_domain_model(
        cls, offers_kpi_summary: OffersKpiSummaryDomainModel
    ) -> "OffersKpiSummarySerializer":
        return cls(
            total_discount_given=AmountSerializer(
                amount=offers_kpi_summary.total_discount_amount,
                currency=offers_kpi_summary.amount_currency,
            ),
            discount_percentage_of_revenue=offers_kpi_summary.discount_percentage_of_revenue,
            average_discount_per_booking=offers_kpi_summary.average_discount_per_booking,
            bookings_with_discount_percentage=offers_kpi_summary.bookings_with_discount_percentage,
            net_revenue_after_discount=AmountSerializer(
                amount=offers_kpi_summary.net_revenue_after_discount,
                currency=offers_kpi_summary.amount_currency,
            ),
        )


class OfferLineItemSerializer(ApiSerializerBaseModel):
    offer_id: str
    title: str
    offer_type: OfferTypeEnum
    offer_value: float
    offer_currency: str
    offer_on: BookingTypeEnum
    applicable_on: (
        OfferApplicabilityEnum  # conditions (coupon code, user segment, payment method, etc.)
    )
    min_booking_amount: AmountSerializer
    max_discount_cap: (
        float  # for percentage discounts, this is the maximum discount amount that can be applied
    )
    per_user_limit: int
    stackable: bool
    usage_count: int
    total_discount_given: AmountSerializer
    cost_bearer: OfferCostBearerEnum
    created_at: AwareDatetime
    validity_from: AwareDatetime
    validity_to: AwareDatetime
    offer_status: OfferStatusEnum

    @classmethod
    def from_domain_model(cls, offer: OfferDomainModel) -> "OfferLineItemSerializer":
        return cls(
            offer_id=offer.offer_id,
            title=offer.title,
            offer_type=offer.offer_type,
            offer_value=offer.offer_value,
            offer_currency=offer.offer_currency,
            offer_on=offer.offer_on,
            applicable_on=offer.applicable_on,
            min_booking_amount=AmountSerializer(
                amount=offer.min_booking_amount, currency=offer.offer_currency
            ),
            max_discount_cap=offer.max_discount_cap,
            per_user_limit=offer.per_user_limit,
            stackable=offer.stackable,
            usage_count=offer.usage_count,
            total_discount_given=AmountSerializer(
                amount=offer.total_discount_given, currency=offer.offer_currency
            ),
            cost_bearer=offer.cost_bearer,
            created_at=offer.created_at,
            validity_from=offer.validity_from,
            validity_to=offer.validity_to,
            offer_status=offer.offer_status,
        )
