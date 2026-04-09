from enum import StrEnum


class CustomerTierEnum(StrEnum):
    """Enum to represent different user tiers (e.g., Novus, Aurea, Privé, Elite, Échelon)"""

    NOVUS = "Novus"
    AUREA = "Aurea"
    PRIVE = "Privé"
    ELITE = "Elite"
    ECHELON = "Échelon"


# TODO: implement automated rewards system
# Rewards system explained


# Tier

# Requirements

# TJ Coins Multiplier

# Benefits

# Novus

# First-time booking

# 1000 per ₹1 Lakh spend

# Welcome reward, introductory perks, TJ Coins.

# Aurea

# Second booking

# 1000 per ₹1 Lakh spend

# Repeat traveler recognition, TJ Coins bonus.

# Privé

# 5 bookings + ≥₹5 Lakh total spend (rolling 12 months)

# 2000 per ₹1 Lakh spend

# Complimentary digital concierge, flexible booking & waived cancellation fees (48h window for trips booked ≥2 months ahead), non-room vouchers (wine, spa, dining, activities) up to ₹1000 ( most vouchers given will be within 200)

# Elite

# ≥5 bookings/year + ≥₹10 Lakh annual spend

# 3000 per ₹1 Lakh spend

# All Privé benefits + invite-only private sales, priority promotions,  complimentary travel insurance, first access to partner luxury hotels, resorts, and airline upgrades.

# Échelon

# Elite + Top 50 spenders/year

# 5000 per ₹1 Lakh spend

# All Elite benefits + virtual private consultation & dedicated relationship manager, concierge-curated experiences, first access to new luxury properties, VIP experiences


class CustomerStatusEnum(StrEnum):
    """Enum to represent different user statuses (e.g., Active, Inactive)"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REPEAT = "repeat"
    LOYAL = "loyal"


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


class TransactionTypeEnum(StrEnum):
    """Enum to represent different transaction types (e.g., Payment, Refund)"""

    PAYMENT = "payment"
    REFUND = "refund"


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

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SupportTicketStatusEnum(StrEnum):
    """Enum to represent different support ticket statuses (e.g., Open, In Progress, Closed)"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class SupportCategoryEnum(StrEnum):
    """Enum to represent different support ticket categories (e.g., Booking Issue, Payment Issue, General Inquiry)"""

    BOOKING_ISSUE = "booking_issue"
    PAYMENT_ISSUE = "payment_issue"
    GENERAL_INQUIRY = "general_inquiry"


class OfferTypeEnum(StrEnum):
    """Enum to represent different offer types (e.g., Percentage Discount, Flat Discount, Special Price)"""

    PERCENTAGE_DISCOUNT = "percentage_discount"
    FLAT_DISCOUNT = "flat_discount"
    SPECIAL_PRICE = "special_price"


class OfferCostBearerEnum(StrEnum):
    """Enum to represent different offer cost bearers (e.g., Merchant, Platform)"""

    PLATFORM = "platform"
    BANK = "bank"
    PARTNER = "partner"


class OfferStatusEnum(StrEnum):
    """Enum to represent different offer statuses (e.g., Active, Expired, Upcoming)"""

    ACTIVE = "active"
    SCHEDULED = "scheduled"
    EXPIRED = "expired"


class OfferApplicabilityEnum(StrEnum):
    """Enum to represent different offer applicability conditions (e.g., Coupon Code, User Segment, Payment Method)"""

    COUPON_CODE = "coupon_code"
    USER_SEGMENT = "user_segment"
    PAYMENT_METHOD = "payment_method"


class PropertySourceEnum(StrEnum):
    """Enum to represent different property sources (e.g., Direct, OTA, Channel Manager)"""

    EXTRAENET = "extranet"
    API = "api"
    OTA = "ota"
    CHANNEL_MANAGER = "channel_manager"


class PropertyStatusEnum(StrEnum):
    """Enum to represent different property statuses (e.g., Active, Pending Approval, Rejected, Suspended)"""

    ACTIVE = "active"
    DORMANT = "dormant"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class PartnerKYCStatusEnum(StrEnum):
    """Enum to represent different partner KYC statuses (e.g., Pending, Approved, Rejected)"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PartnerStatusControlActionEnum(StrEnum):
    """Enum to represent different partner status control actions (e.g., Activate, Suspend, Reject)"""

    APPROVE = "approve"
    REJECT = "reject"
    DEACTIVATE = "deactivate"
    REQUEST_UPDATE = "request_update"
