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


class PersonalCalendarEventTypeEnum(StrEnum):
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    SPECIAL_OCCASION = "special_occasion"


class BirthdayForEnum(StrEnum):
    MY_BIRTHDAY = "my_birthday"
    SPOUSE_BIRTHDAY = "spouse_birthday"
    FATHER_BIRTHDAY = "father_birthday"
    MOTHER_BIRTHDAY = "mother_birthday"
    CHILD_BIRTHDAY = "child_birthday"


class AnniversaryForEnum(StrEnum):
    MY_ANNIVERSARY = "my_anniversary"
    PARENTS = "parents"
    IN_LAWS = "in_laws"
    OTHERS = "others"


class HolidayTypeEnum(StrEnum):
    AFRICAN_SAFARIS_AND_WILDLIFE_TOURS = "African Safaris & Wildlife Tours"
    LUXURY_STAYS_HOTELS_VILLAS = "Luxury Stays Hotels/Villas"
    WELLNESS_AND_SPA_RETREATS = "Wellness & Spa Retreats"
    HONEYMOONS_AND_ROMANTIC_HOLIDAYS = "Honeymoons & Romantic Holidays"
    FAMILY_LUXURY_HOLIDAYS = "Family Luxury Holidays"
    SKI_GOLF_AND_CASINO_TRIPS = "Ski, Golf & Casino Trips"
    CULTURE_FOOD_AND_SHOPPING_TOURS = "Culture, Food & Shopping Tours"
    ALL_INCLUSIVE_LUXURY_DEALS = "All-Inclusive Luxury Deals"
    ONCE_IN_A_LIFE_TIME_TRIPS = "Once In a Life Time trips"
    DISNEY_AND_EURAIL_TICKETS = "Disney & Eurail Tickets"
    SIGNATURE_EXPERIENCES = "Signature Experiences"


HOLIDAY_TYPE_LIST: tuple[str, ...] = tuple(item.value for item in HolidayTypeEnum)
