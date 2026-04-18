from dataclasses import dataclass
from datetime import date, datetime, timedelta

from luxtj.domain.enums import OfferStatusEnum
from luxtj.utils import mockutils


@dataclass
class OfferPricingSummaryDomainModel:
    total_properties: int
    active_offers: int
    avg_commission_percentage: float
    seasonal_pricing_active: int

    @classmethod
    def generate_mock(cls) -> OfferPricingSummaryDomainModel:
        return cls(
            total_properties=mockutils.random.randint(50, 300),
            active_offers=mockutils.random.randint(20, 120),
            avg_commission_percentage=round(mockutils.random.uniform(5.0, 25.0), 2),
            seasonal_pricing_active=mockutils.random.randint(10, 90),
        )


@dataclass
class OfferPricingPropertyLineItemDomainModel:
    property_id: str
    property_name: str
    location: str
    base_price_amount: float
    base_price_currency: str
    current_offer: str | None
    last_updated: datetime

    @classmethod
    def generate_mock(cls) -> OfferPricingPropertyLineItemDomainModel:
        return cls(
            property_id=mockutils.random_user_id(),
            property_name=mockutils.random_property_name(),
            location=mockutils.random_property_location(),
            base_price_amount=mockutils.random_booking_amount(2000, 25000),
            base_price_currency="INR",
            current_offer=mockutils.random.choice(
                [
                    "Summer Sale",
                    "Weekend Saver",
                    "Early Bird",
                    None,
                ]
            ),
            last_updated=mockutils.random_date_from_past_days(),
        )


@dataclass
class OfferPricingActivityLineItemDomainModel:
    activity_id: str
    activity_name: str
    location: str
    base_price_amount: float
    base_price_currency: str
    offer: str | None
    commission_percentage: float

    @classmethod
    def generate_mock(cls) -> OfferPricingActivityLineItemDomainModel:
        return cls(
            activity_id=mockutils.random_user_id(),
            activity_name=mockutils.random.choice(
                [
                    "Skiing",
                    "Trekking",
                    "Shikara Ride",
                    "Safari",
                ]
            ),
            location=mockutils.random_property_location(),
            base_price_amount=mockutils.random_booking_amount(500, 8000),
            base_price_currency="INR",
            offer=mockutils.random.choice(["Adventure Week", "Festive Offer", None]),
            commission_percentage=round(mockutils.random.uniform(5.0, 22.0), 2),
        )


@dataclass
class OfferPricingCommissionLineItemDomainModel:
    commission_id: str
    partner_type: str
    commission_percentage: float
    last_updated: datetime

    @classmethod
    def generate_mock(cls) -> OfferPricingCommissionLineItemDomainModel:
        return cls(
            commission_id=mockutils.random_user_id(),
            partner_type=mockutils.random.choice(["Property", "Activity", "Destination"]),
            commission_percentage=round(mockutils.random.uniform(5.0, 25.0), 2),
            last_updated=mockutils.random_date_from_past_days(),
        )


@dataclass
class PartnerOfferLineItemDomainModel:
    offer_id: str
    offer_name: str
    applicable_to: str
    applies_to_item: str
    discount_percentage: float | None
    flat_discount_amount: float | None
    flat_discount_currency: str | None
    start_date: date
    end_date: date
    min_nights: int | None
    min_booking_amount: float | None
    min_booking_currency: str | None
    status: OfferStatusEnum

    @classmethod
    def generate_mock(cls) -> PartnerOfferLineItemDomainModel:
        has_percentage_discount = mockutils.random.choice([True, False])
        base_start_date = mockutils.random_date_from_past_days(90).date()
        end_date = base_start_date + timedelta(days=mockutils.random.randint(7, 45))
        return cls(
            offer_id=mockutils.random_booking_id(),
            offer_name=mockutils.random_offer_title(),
            applicable_to=mockutils.random.choice(["Property", "Activity", "Destination"]),
            applies_to_item=mockutils.random.choice(
                [
                    mockutils.random_property_name(),
                    "Skiing",
                    "Leh",
                ]
            ),
            discount_percentage=round(mockutils.random.uniform(5.0, 40.0), 2)
            if has_percentage_discount
            else None,
            flat_discount_amount=mockutils.random_booking_amount(500, 5000)
            if not has_percentage_discount
            else None,
            flat_discount_currency="INR" if not has_percentage_discount else None,
            start_date=base_start_date,
            end_date=end_date,
            min_nights=mockutils.random.randint(1, 5),
            min_booking_amount=mockutils.random_booking_amount(2000, 25000),
            min_booking_currency="INR",
            status=mockutils.random.choice(list(OfferStatusEnum)),
        )


@dataclass
class OfferPricingSeasonalLineItemDomainModel:
    seasonal_price_id: str
    property_name: str
    season: str
    price_amount: float
    price_currency: str
    start_date: date
    end_date: date

    @classmethod
    def generate_mock(cls) -> OfferPricingSeasonalLineItemDomainModel:
        base_start_date = mockutils.random_date_from_past_days(120).date()
        end_date = base_start_date + timedelta(days=mockutils.random.randint(10, 90))
        return cls(
            seasonal_price_id=mockutils.random_booking_id(),
            property_name=mockutils.random_property_name(),
            season=mockutils.random.choice(["Summer", "Winter", "Festive"]),
            price_amount=mockutils.random_booking_amount(3000, 30000),
            price_currency="INR",
            start_date=base_start_date,
            end_date=end_date,
        )
