from pydantic import AwareDatetime

from admin_api.audit_logs.domainmodel import (
    AuditLogActionCategoryEnum,
    AuditLogActorDomainModel,
    AuditLogActorTypeEnum,
    AuditLogEventDomainModel,
    AuditLogSeverityEnum,
)
from common.serializerlib import ApiSerializerBaseModel


class AuditLogActor(ApiSerializerBaseModel):
    type: AuditLogActorTypeEnum
    id: str
    email: str | None
    display_name: str | None
    ip_address: str | None
    user_agent: str | None

    @classmethod
    def from_domain_model(cls, domain_model: AuditLogActorDomainModel) -> AuditLogActor:
        return cls(
            type=domain_model.type,
            id=domain_model.id,
            email=domain_model.email,
            display_name=domain_model.display_name,
            ip_address=domain_model.ip_address,
            user_agent=domain_model.user_agent,
        )


class AuditLogEvent(ApiSerializerBaseModel):
    id: str
    timestamp: AwareDatetime
    action: str
    category: AuditLogActionCategoryEnum
    severity: AuditLogSeverityEnum
    actor: AuditLogActor
    tags: list[str]
    request_id: str
    correlation_id: str

    @classmethod
    def from_domain_model(cls, domain_model: AuditLogEventDomainModel) -> AuditLogEvent:
        return cls(
            id=domain_model.id,
            timestamp=domain_model.timestamp,
            action=domain_model.action,
            category=domain_model.category,
            severity=domain_model.severity,
            actor=AuditLogActor.from_domain_model(domain_model.actor),
            tags=domain_model.tags,
            request_id=domain_model.request_id,
            correlation_id=domain_model.correlation_id,
        )
