from __future__ import annotations

from pydantic import AwareDatetime, Field

from admin_api.reports.partners.domainmodel import (
    PartnerOptionDomainModel,
    PartnerReportDomainModel,
    PartnerReportRowDomainModel,
    PartnerReportTotalsDomainModel,
    PartnerReportTypeEnum,
    PartnerTypeEnum,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class PartnerReportQuery(ApiSerializerBaseModel):
    report_type: PartnerReportTypeEnum = Field(
        PartnerReportTypeEnum.PARTNER,
        alias="reportType",
        description="Partner report to return for the dashboard tab",
    )


class PartnerSearchQuery(ApiSerializerBaseModel):
    partner_type: PartnerTypeEnum = Field(
        ...,
        alias="partnerType",
        description="Partner lookup type. Supported values are partner, b2b, and affiliate.",
    )
    search_query: str | None = Field(
        None,
        alias="q",
        description="User-entered text used to search partners",
    )


class PartnerOption(ApiSerializerBaseModel):
    partner_type: PartnerTypeEnum
    partner_id: str
    partner_name: str

    @classmethod
    def from_domain_model(cls, domain_model: PartnerOptionDomainModel) -> PartnerOption:
        return cls(
            partner_type=domain_model.partner_type,
            partner_id=domain_model.partner_id,
            partner_name=domain_model.partner_name,
        )


class PartnerReportTotals(ApiSerializerBaseModel):
    revenue: AmountSerializer
    booking_count: int
    lead_count: int
    commission: AmountSerializer
    average_booking_value: AmountSerializer
    conversion_rate: float

    @classmethod
    def from_domain_model(cls, domain_model: PartnerReportTotalsDomainModel) -> PartnerReportTotals:
        return cls(
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.currency,
            ),
            booking_count=domain_model.booking_count,
            lead_count=domain_model.lead_count,
            commission=AmountSerializer(
                amount=domain_model.commission_amount,
                currency=domain_model.currency,
            ),
            average_booking_value=AmountSerializer(
                amount=domain_model.average_booking_value,
                currency=domain_model.currency,
            ),
            conversion_rate=domain_model.conversion_rate,
        )


class PartnerReportRow(ApiSerializerBaseModel):
    partner_type: PartnerTypeEnum
    partner_id: str
    partner_name: str
    revenue: AmountSerializer
    booking_count: int
    lead_count: int
    commission: AmountSerializer
    average_booking_value: AmountSerializer
    conversion_rate: float
    performance_score: float

    @classmethod
    def from_domain_model(cls, domain_model: PartnerReportRowDomainModel) -> PartnerReportRow:
        return cls(
            partner_type=domain_model.partner_type,
            partner_id=domain_model.partner_id,
            partner_name=domain_model.partner_name,
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.currency,
            ),
            booking_count=domain_model.booking_count,
            lead_count=domain_model.lead_count,
            commission=AmountSerializer(
                amount=domain_model.commission_amount,
                currency=domain_model.currency,
            ),
            average_booking_value=AmountSerializer(
                amount=domain_model.average_booking_value,
                currency=domain_model.currency,
            ),
            conversion_rate=domain_model.conversion_rate,
            performance_score=domain_model.performance_score,
        )


class PartnerReport(ApiSerializerBaseModel):
    report_type: PartnerReportTypeEnum
    title: str
    generated_at: AwareDatetime
    currency: str
    totals: PartnerReportTotals
    rows: list[PartnerReportRow]

    @classmethod
    def from_domain_model(cls, domain_model: PartnerReportDomainModel) -> PartnerReport:
        return cls(
            report_type=domain_model.report_type,
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            totals=PartnerReportTotals.from_domain_model(domain_model.totals),
            rows=[PartnerReportRow.from_domain_model(row) for row in domain_model.rows],
        )
