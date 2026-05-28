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
