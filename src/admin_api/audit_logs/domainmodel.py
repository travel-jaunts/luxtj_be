from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from luxtj.utils import mockutils


class AuditLogActionCategoryEnum(StrEnum):
    AUTHENTICATION = "authentication"
    USER_MANAGEMENT = "user_management"
    BOOKING = "booking"
    PAYMENT = "payment"
    PARTNER = "partner"
    SYSTEM = "system"


class AuditLogSeverityEnum(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogActorTypeEnum(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SERVICE = "service"
    SYSTEM = "system"


@dataclass
class AuditLogActorDomainModel:
    type: AuditLogActorTypeEnum
    id: str
    email: str | None
    display_name: str | None
    ip_address: str | None
    user_agent: str | None

    @classmethod
    def generate_mock(cls) -> AuditLogActorDomainModel:
        first_name = mockutils.random_user_first_name()
        last_name = mockutils.random_user_last_name()
        return cls(
            type=mockutils.random.choice(
                [
                    AuditLogActorTypeEnum.USER,
                    AuditLogActorTypeEnum.ADMIN,
                    AuditLogActorTypeEnum.SERVICE,
                ]
            ),
            id=f"usr_{mockutils.random.randint(100, 999)}",
            email=f"{first_name.lower()}.{last_name.lower()}@example.com",
            display_name=f"{first_name} {last_name}",
            ip_address=f"203.0.113.{mockutils.random.randint(1, 254)}",
            user_agent="Mozilla/5.0",
        )


@dataclass
class AuditLogEventDomainModel:
    id: str
    timestamp: datetime
    action: str
    category: AuditLogActionCategoryEnum
    severity: AuditLogSeverityEnum
    actor: AuditLogActorDomainModel
    tags: list[str]
    request_id: str
    correlation_id: str

    @classmethod
    def generate_mock(
        cls,
        *,
        from_datetime: datetime,
        to_datetime: datetime,
    ) -> AuditLogEventDomainModel:
        event_timestamp = from_datetime + (to_datetime - from_datetime) * mockutils.random.random()
        category = mockutils.random.choice(list(AuditLogActionCategoryEnum))
        action = mockutils.random.choice(
            {
                AuditLogActionCategoryEnum.AUTHENTICATION: [
                    "user.login",
                    "user.logout",
                    "user.password_reset",
                ],
                AuditLogActionCategoryEnum.USER_MANAGEMENT: [
                    "user.created",
                    "user.updated",
                    "user.disabled",
                ],
                AuditLogActionCategoryEnum.BOOKING: [
                    "booking.created",
                    "booking.cancelled",
                    "booking.updated",
                ],
                AuditLogActionCategoryEnum.PAYMENT: [
                    "payment.captured",
                    "payment.refunded",
                    "payment.failed",
                ],
                AuditLogActionCategoryEnum.PARTNER: [
                    "partner.approved",
                    "partner.suspended",
                    "partner.updated",
                ],
                AuditLogActionCategoryEnum.SYSTEM: [
                    "system.config_updated",
                    "system.job_started",
                    "system.job_failed",
                ],
            }[category]
        )
        severity = (
            AuditLogSeverityEnum.ERROR
            if action.endswith("failed")
            else mockutils.random.choice(
                [
                    AuditLogSeverityEnum.INFO,
                    AuditLogSeverityEnum.INFO,
                    AuditLogSeverityEnum.WARNING,
                ]
            )
        )

        return cls(
            id=f"evt_{mockutils.random.randint(10**20, 10**21 - 1)}",
            timestamp=event_timestamp,
            action=action,
            category=category,
            severity=severity,
            actor=AuditLogActorDomainModel.generate_mock(),
            tags=[category.value, action.split(".")[0]],
            request_id=f"req_{mockutils.random.randint(10000, 99999)}",
            correlation_id=f"corr_{mockutils.random.randint(10000, 99999)}",
        )


def date_range_to_utc_datetimes(
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[datetime, datetime]:
    end_datetime = to_date or datetime.now(tz=UTC)
    start_datetime = from_date or end_datetime - timedelta(days=7)
    return start_datetime, end_datetime
