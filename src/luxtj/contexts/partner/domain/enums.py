from enum import StrEnum


class PropertySourceEnum(StrEnum):
    EXTRAENET = "extranet"
    API = "api"
    OTA = "ota"
    CHANNEL_MANAGER = "channel_manager"


class PropertyStatusEnum(StrEnum):
    ACTIVE = "active"
    DORMANT = "dormant"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class PartnerKYCStatusEnum(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PartnerStatusControlActionEnum(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    DEACTIVATE = "deactivate"
    REQUEST_UPDATE = "request_update"


class ApprovalStatusEnum(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalControlActionEnum(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request-changes"


class ApprovalTypeEnum(StrEnum):
    CONTENT = "content"
    KYC = "kyc"


class PartnerTypeEnum(StrEnum):
    PARTNER = "partner"
    B2B = "b2b"
    AFFILIATE = "affiliate"


class OfferTypeEnum(StrEnum):
    PERCENTAGE_DISCOUNT = "percentage_discount"
    FLAT_DISCOUNT = "flat_discount"
    SPECIAL_PRICE = "special_price"


class OfferStatusEnum(StrEnum):
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    EXPIRED = "expired"
