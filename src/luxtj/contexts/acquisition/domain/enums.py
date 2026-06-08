from enum import StrEnum


class WaitlistStatus(StrEnum):
    PENDING = "pending"
    NOTIFIED = "notified"
    CONVERTED = "converted"
    REJECTED = "rejected"
