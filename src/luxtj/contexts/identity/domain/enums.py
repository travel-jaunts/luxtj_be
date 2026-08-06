from enum import StrEnum


class UserTypeEnum(StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    PARTNER = "partner"
    B2C = "b2c"


class UserStatusEnum(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
