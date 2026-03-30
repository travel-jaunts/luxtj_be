from enum import StrEnum


class BookingStatusEnum(StrEnum):
    """Enum to represent different booking statuses (e.g., Confirmed, Cancelled, Pending)
    - more statuses to be added
    """

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class BookingSourceEnum(StrEnum):
    """Enum to represent different booking sources (e.g., Website, Mobile App, Third-Party)
    - more sources to be added
    """

    AFFILIATE = "affiliate"
    MOBILE_APP = "mobile_app"
    WEB_APP = "web_app"
    B2B_AGENT = "b2b_agent"


class PaymentStatusEnum(StrEnum):
    """Enum to represent different payment statuses (e.g., Completed, Failed, Refunded)
    - more statuses to be added
    """

    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethodEnum(StrEnum):
    """Enum to represent different payment methods (e.g., Credit Card, PayPal, Bank Transfer)
    - more methods to be added
    """

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"


class PaymentSourceEnum(StrEnum):
    """Enum to represent different payment sources (e.g., Website, Mobile App, Third-Party)
    - more sources to be added
    """

    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"


class SupportTicketPriorityEnum(StrEnum):
    """Enum to represent different support ticket priorities (e.g., Low, Medium, High)
    - more priorities to be added
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
