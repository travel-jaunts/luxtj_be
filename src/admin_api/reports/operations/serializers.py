from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, Field

from admin_api.reports.operations.domainmodel import (
    OperationsApprovalSummaryDomainModel,
    OperationsReportDomainModel,
    PartnerResponseTimeRowDomainModel,
    PartnerResponseTimeSummaryDomainModel,
    SupportResolutionTimeSummaryDomainModel,
)
from common.serializerlib import ApiSerializerBaseModel
from luxtj.domain.enums import PartnerTypeEnum


class OperationsReportQuery(ApiSerializerBaseModel):
    from_date: date | None = Field(None, description="Start date for the operations overview")
    to_date: date | None = Field(None, description="End date for the operations overview")


class OperationsApprovalSummary(ApiSerializerBaseModel):
    pending_approvals: int
    kyc_pending: int
    content_updates: int
    new_partners: int
    oldest_pending_hours: float

    @classmethod
    def from_domain_model(
        cls, domain_model: OperationsApprovalSummaryDomainModel
    ) -> OperationsApprovalSummary:
        return cls(
            pending_approvals=domain_model.pending_approvals,
            kyc_pending=domain_model.kyc_pending,
            content_updates=domain_model.content_updates,
            new_partners=domain_model.new_partners,
            oldest_pending_hours=domain_model.oldest_pending_hours,
        )


class PartnerResponseTimeRow(ApiSerializerBaseModel):
    partner_type: PartnerTypeEnum
    average_response_time_hours: float
    pending_response_count: int
    response_sla_breach_count: int

    @classmethod
    def from_domain_model(
        cls, domain_model: PartnerResponseTimeRowDomainModel
    ) -> PartnerResponseTimeRow:
        return cls(
            partner_type=domain_model.partner_type,
            average_response_time_hours=domain_model.average_response_time_hours,
            pending_response_count=domain_model.pending_response_count,
            response_sla_breach_count=domain_model.response_sla_breach_count,
        )


class PartnerResponseTimeSummary(ApiSerializerBaseModel):
    average_response_time_hours: float
    pending_response_count: int
    response_sla_breach_count: int
    rows: list[PartnerResponseTimeRow]

    @classmethod
    def from_domain_model(
        cls, domain_model: PartnerResponseTimeSummaryDomainModel
    ) -> PartnerResponseTimeSummary:
        return cls(
            average_response_time_hours=domain_model.average_response_time_hours,
            pending_response_count=domain_model.pending_response_count,
            response_sla_breach_count=domain_model.response_sla_breach_count,
            rows=[PartnerResponseTimeRow.from_domain_model(row) for row in domain_model.rows],
        )


class SupportResolutionTimeSummary(ApiSerializerBaseModel):
    total_tickets: int
    open_tickets: int
    average_resolution_time_hours: float
    escalation_rate_percent: float
    support_sla_breach_count: int

    @classmethod
    def from_domain_model(
        cls, domain_model: SupportResolutionTimeSummaryDomainModel
    ) -> SupportResolutionTimeSummary:
        return cls(
            total_tickets=domain_model.total_tickets,
            open_tickets=domain_model.open_tickets,
            average_resolution_time_hours=domain_model.average_resolution_time_hours,
            escalation_rate_percent=domain_model.escalation_rate_percent,
            support_sla_breach_count=domain_model.support_sla_breach_count,
        )


class OperationsReport(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    from_date: date | None
    to_date: date | None
    approvals_pending: OperationsApprovalSummary
    partner_response_time: PartnerResponseTimeSummary
    support_resolution_time: SupportResolutionTimeSummary

    @classmethod
    def from_domain_model(cls, domain_model: OperationsReportDomainModel) -> OperationsReport:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            from_date=domain_model.from_date,
            to_date=domain_model.to_date,
            approvals_pending=OperationsApprovalSummary.from_domain_model(
                domain_model.approvals_pending
            ),
            partner_response_time=PartnerResponseTimeSummary.from_domain_model(
                domain_model.partner_response_time
            ),
            support_resolution_time=SupportResolutionTimeSummary.from_domain_model(
                domain_model.support_resolution_time
            ),
        )
