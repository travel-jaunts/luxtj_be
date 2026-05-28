from enum import StrEnum


class BookingTypeEnum(StrEnum):
    FLIGHT = "flight"
    STAYS = "stays"
    PACKAGE = "package"
    EXPERIENCE = "experience"
    OTHERS = "others"


class OfferTypeEnum(StrEnum):
    PERCENTAGE_DISCOUNT = "percentage_discount"
    FLAT_DISCOUNT = "flat_discount"
    SPECIAL_PRICE = "special_price"


class OfferCostBearerEnum(StrEnum):
    PLATFORM = "platform"
    BANK = "bank"
    PARTNER = "partner"


class OfferStatusEnum(StrEnum):
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    EXPIRED = "expired"


class OfferApplicabilityEnum(StrEnum):
    COUPON_CODE = "coupon_code"
    USER_SEGMENT = "user_segment"
    PAYMENT_METHOD = "payment_method"


class PartnerTypeEnum(StrEnum):
    PARTNER = "partner"
    B2B = "b2b"
    AFFILIATE = "affiliate"
