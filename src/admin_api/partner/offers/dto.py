from dataclasses import dataclass
from datetime import date

from luxtj.domain.enums import OfferStatusEnum


@dataclass
class UpdatePropertyPricingDTO:
    base_price_amount: float
    base_price_currency: str
    commission_percentage: float
    seasonal_price_amount: float
    seasonal_price_currency: str


@dataclass
class UpdateActivityPricingDTO:
    base_price_amount: float
    base_price_currency: str
    commission_percentage: float
    seasonal_price_amount: float
    seasonal_price_currency: str


@dataclass
class UpdateCommissionDTO:
    commission_percentage: float


@dataclass
class CreatePartnerOfferDTO:
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


@dataclass
class UpdatePartnerOfferDTO:
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


@dataclass
class UpdateSeasonalPricingDTO:
    property_name: str
    season: str
    price_amount: float
    price_currency: str
    start_date: date
    end_date: date
