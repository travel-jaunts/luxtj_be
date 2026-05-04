from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from admin_api.customer.support.domainmodel import SupportKpiSummary
from admin_api.partner.approvals.domainmodel import ApprovalSummaryDomainModel
from luxtj.domain.enums import PartnerTypeEnum
from luxtj.utils import mockutils


@dataclass
class OperationsApprovalSummaryDomainModel:
    pending_approvals: int
    kyc_pending: int
    content_updates: int
    new_partners: int
    oldest_pending_hours: float

    @classmethod
    def generate_mock(cls) -> OperationsApprovalSummaryDomainModel:
        approval_summary = ApprovalSummaryDomainModel.generate_mock()
        return cls(
            pending_approvals=approval_summary.pending_approvals,
            kyc_pending=approval_summary.kyc_pending,
            content_updates=approval_summary.content_updates,
            new_partners=approval_summary.new_partners,
            oldest_pending_hours=round(mockutils.random.uniform(6.0, 120.0), 2),
        )


@dataclass
class PartnerResponseTimeRowDomainModel:
    partner_type: PartnerTypeEnum
    average_response_time_hours: float
    pending_response_count: int
    response_sla_breach_count: int


@dataclass
class PartnerResponseTimeSummaryDomainModel:
    average_response_time_hours: float
    pending_response_count: int
    response_sla_breach_count: int
    rows: list[PartnerResponseTimeRowDomainModel]

    @classmethod
    def generate_mock(cls) -> PartnerResponseTimeSummaryDomainModel:
        rows = [
            PartnerResponseTimeRowDomainModel(
                partner_type=partner_type,
                average_response_time_hours=round(mockutils.random.uniform(1.0, 36.0), 2),
                pending_response_count=mockutils.random.randint(0, 80),
                response_sla_breach_count=mockutils.random.randint(0, 20),
            )
            for partner_type in PartnerTypeEnum
        ]
        return cls(
            average_response_time_hours=round(
                sum(row.average_response_time_hours for row in rows) / len(rows),
                2,
            ),
            pending_response_count=sum(row.pending_response_count for row in rows),
            response_sla_breach_count=sum(row.response_sla_breach_count for row in rows),
            rows=rows,
        )


@dataclass
class SupportResolutionTimeSummaryDomainModel:
    total_tickets: int
    open_tickets: int
    average_resolution_time_hours: float
    escalation_rate_percent: float
    support_sla_breach_count: int

    @classmethod
    def generate_mock(cls) -> SupportResolutionTimeSummaryDomainModel:
        support_summary = SupportKpiSummary.generate_mock()
        return cls(
            total_tickets=support_summary.total_tickets,
            open_tickets=support_summary.open_tickets,
            average_resolution_time_hours=round(
                support_summary.average_resolution_time_hours,
                2,
            ),
            escalation_rate_percent=round(support_summary.escalation_rate_percent, 2),
            support_sla_breach_count=mockutils.random.randint(0, support_summary.total_tickets),
        )


@dataclass
class OperationsReportDomainModel:
    title: str
    generated_at: datetime
    from_date: date | None
    to_date: date | None
    approvals_pending: OperationsApprovalSummaryDomainModel
    partner_response_time: PartnerResponseTimeSummaryDomainModel
    support_resolution_time: SupportResolutionTimeSummaryDomainModel
