from enum import StrEnum


class CampaignChannelEnum(StrEnum):
    """Outbound campaign channels supported by marketing."""

    EMAIL = "email"
    WHATSAPP = "whatsApp"
    SMS = "SMS"
    PUSH_NOTIFICATIONS = "push notifications"


class ScheduleFrequencyEnum(StrEnum):
    ONE_TIME = "one-time"
    RECURRING = "recurring"


class CampaignStatusEnum(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OfferTypeEnum(StrEnum):
    FLAT = "flat"
    PERCENTAGE_OFF = "percentage_off"
    BUNDLE = "bundle"
    REFERRAL = "referral"


class OfferStatusEnum(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PAUSED = "paused"
    RESCINDED = "rescinded"
    DELETED = "deleted"
