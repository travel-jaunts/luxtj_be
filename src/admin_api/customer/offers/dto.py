from dataclasses import dataclass
from datetime import datetime

from luxtj.domain.enums import (
    BookingTypeEnum,
    OfferApplicabilityEnum,
    OfferCostBearerEnum,
    OfferStatusEnum,
    OfferTypeEnum,
)


@dataclass
class CreateOfferDTO:
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
    cost_bearer: OfferCostBearerEnum
    validity_from: datetime
    validity_to: datetime
    offer_status: OfferStatusEnum


@dataclass
class UpdateOfferDTO:
    title: str
    offer_value: float
    offer_currency: str
    min_booking_amount: float
    max_discount_cap: float
    per_user_limit: int
    stackable: bool
    cost_bearer: OfferCostBearerEnum
    validity_from: datetime
    validity_to: datetime
    offer_status: OfferStatusEnum
