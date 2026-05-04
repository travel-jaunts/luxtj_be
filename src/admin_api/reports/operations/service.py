from __future__ import annotations

from datetime import UTC, date, datetime

from admin_api.reports.operations.domainmodel import (
    OperationsApprovalSummaryDomainModel,
    OperationsReportDomainModel,
    PartnerResponseTimeSummaryDomainModel,
    SupportResolutionTimeSummaryDomainModel,
)


class OperationsReportService:
    async def get_report(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> OperationsReportDomainModel:
        return OperationsReportDomainModel(
            title="Operations Overview",
            generated_at=datetime.now(tz=UTC),
            from_date=from_date,
            to_date=to_date,
            approvals_pending=OperationsApprovalSummaryDomainModel.generate_mock(),
            partner_response_time=PartnerResponseTimeSummaryDomainModel.generate_mock(),
            support_resolution_time=SupportResolutionTimeSummaryDomainModel.generate_mock(),
        )
