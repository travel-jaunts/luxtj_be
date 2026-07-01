from enum import StrEnum


class CustomerTierEnum(StrEnum):
    NOVUS = "Novus"
    AUREA = "Aurea"
    PRIVE = "Privé"
    ELITE = "Elite"
    ECHELON = "Échelon"


class CustomerStatusEnum(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REPEAT = "repeat"
    LOYAL = "loyal"


class BookingTypeEnum(StrEnum):
    FLIGHT = "flight"
    STAYS = "stays"
    PACKAGE = "package"
    EXPERIENCE = "experience"
    OTHERS = "others"


class BookingStatusEnum(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class BookingSourceEnum(StrEnum):
    AFFILIATE = "affiliate"
    MOBILE_APP = "mobile_app"
    WEB_APP = "web_app"
    B2B_AGENT = "b2b_agent"


class TransactionTypeEnum(StrEnum):
    PAYMENT = "payment"
    REFUND = "refund"


class PaymentStatusEnum(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethodEnum(StrEnum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"


class PaymentSourceEnum(StrEnum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"


class RefundStatusEnum(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class SupportTicketPriorityEnum(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SupportTicketStatusEnum(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class SupportCategoryEnum(StrEnum):
    BOOKING_ISSUE = "booking_issue"
    PAYMENT_ISSUE = "payment_issue"
    GENERAL_INQUIRY = "general_inquiry"


class SupportEscalationLevelEnum(StrEnum):
    NONE = "none"
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"


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


class BucketDestinationKindEnum(StrEnum):
    COUNTRY = "country"
    CITY = "city"
    PLACE = "place"
