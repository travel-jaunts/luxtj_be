from dataclasses import dataclass
from datetime import datetime

from luxtj.domain.enums import (
    BookingTypeEnum,
    OfferApplicabilityEnum,
    OfferCostBearerEnum,
    OfferStatusEnum,
    OfferTypeEnum,
)
from luxtj.utils import mockutils


@dataclass
class OffersKpiSummaryDomainModel:
    amount_currency: str
    total_discount_amount: float
    discount_percentage_of_revenue: float
    average_discount_per_booking: float
    bookings_with_discount_percentage: float
    net_revenue_after_discount: float

    @classmethod
    def generate_mock(cls, *, mock_currency: str = "INR") -> OffersKpiSummaryDomainModel:
        return cls(
            amount_currency=mock_currency,
            total_discount_amount=mockutils.random.uniform(1000.0, 10000.0),
            discount_percentage_of_revenue=mockutils.random.uniform(5.0, 20.0),
            average_discount_per_booking=mockutils.random.uniform(10.0, 100.0),
            bookings_with_discount_percentage=mockutils.random.uniform(5.0, 50.0),
            net_revenue_after_discount=mockutils.random.uniform(50000.0, 100000.0),
        )


@dataclass
class OfferDomainModel:
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
    created_at: datetime
    validity_from: datetime
    validity_to: datetime
    offer_status: OfferStatusEnum

    @classmethod
    def generate_mock(cls, *, mock_currency: str = "INR") -> OfferDomainModel:
        return cls(
            offer_id=mockutils.random_booking_id(),
            title=mockutils.random_offer_title(),
            offer_type=mockutils.random.choice(list(OfferTypeEnum)),
            offer_value=mockutils.random.uniform(10.0, 50.0),
            offer_currency=mock_currency,
            offer_on=mockutils.random.choice(list(BookingTypeEnum)),
            applicable_on=mockutils.random.choice(list(OfferApplicabilityEnum)),
            min_booking_amount=mockutils.random.uniform(1000.0, 5000.0),
            max_discount_cap=mockutils.random.uniform(0, 5.0),
            per_user_limit=mockutils.random.randint(1, 5),
            stackable=mockutils.random.choice([True, False]),
            usage_count=mockutils.random.randint(0, 100),
            total_discount_given=mockutils.random.uniform(1000.0, 10000.0),
            cost_bearer=mockutils.random.choice(list(OfferCostBearerEnum)),
            created_at=mockutils.random_registration_date(),
            validity_from=mockutils.random_registration_date(),
            validity_to=mockutils.random_registration_date(),
            offer_status=mockutils.random.choice(list(OfferStatusEnum)),
        )
