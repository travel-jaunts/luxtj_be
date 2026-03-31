from enum import StrEnum


class CustomerTierEnum(StrEnum):
    """Enum to represent different user tiers (e.g., Novus, Aurea, Privé, Elite, Échelon)"""

    NOVUS = "Novus"
    AUREA = "Aurea"
    PRIVE = "Privé"
    ELITE = "Elite"
    ECHELON = "Échelon"


class CustomerStatusEnum(StrEnum):
    """Enum to represent different user statuses (e.g., Active, Inactive)"""

    ACTIVE = "Active"
    INACTIVE = "Inactive"
    REPEAT = "Repeat"
    LOYAL = "Loyal"


class BookingTypeEnum(StrEnum):
    """Enum to represent different booking types (e.g., Flight, Hotel, Car Rental)"""

    FLIGHT = "flight"
    STAYS = "stays"
    PACKAGE = "package"
    EXPERIENCE = "experience"
    OTHERS = "others"


class BookingStatusEnum(StrEnum):
    """Enum to represent different booking statuses (e.g., Confirmed, Cancelled, Pending)"""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class BookingSourceEnum(StrEnum):
    """Enum to represent different booking sources (e.g., Website, Mobile App, Third-Party)"""

    AFFILIATE = "affiliate"
    MOBILE_APP = "mobile_app"
    WEB_APP = "web_app"
    B2B_AGENT = "b2b_agent"


class PaymentStatusEnum(StrEnum):
    """Enum to represent different payment statuses (e.g., Completed, Failed, Refunded)"""

    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethodEnum(StrEnum):
    """Enum to represent different payment methods (e.g., Credit Card, PayPal, Bank Transfer)"""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"


class PaymentSourceEnum(StrEnum):
    """Enum to represent different payment sources (e.g., Website, Mobile App, Third-Party)"""

    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"


class RefundStatusEnum(StrEnum):
    """Enum to represent different refund statuses (e.g., Pending, Processed, Failed)"""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class SupportTicketPriorityEnum(StrEnum):
    """Enum to represent different support ticket priorities (e.g., Low, Medium, High)"""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
