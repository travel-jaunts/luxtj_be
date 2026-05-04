from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from luxtj.domain.enums import PartnerTypeEnum
from luxtj.utils import mockutils


class PartnerReportTypeEnum(StrEnum):
    PARTNER = "partner_performance"
    B2B = "b2b_performance"
    AFFILIATE = "affiliate_performance"


@dataclass
class PartnerOptionDomainModel:
    partner_type: PartnerTypeEnum
    partner_id: str
    partner_name: str


@dataclass
class PartnerReportRowDomainModel:
    partner_type: PartnerTypeEnum
    partner_id: str
    partner_name: str
    revenue_amount: float
    currency: str
    booking_count: int
    lead_count: int
    commission_amount: float
    conversion_rate: float
    performance_score: float

    @property
    def average_booking_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.revenue_amount / self.booking_count, 2)


@dataclass
class PartnerReportTotalsDomainModel:
    revenue_amount: float
    currency: str
    booking_count: int
    lead_count: int
    commission_amount: float

    @property
    def average_booking_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.revenue_amount / self.booking_count, 2)

    @property
    def conversion_rate(self) -> float:
        if self.lead_count == 0:
            return 0.0
        return round((self.booking_count / self.lead_count) * 100, 2)


@dataclass
class PartnerReportDomainModel:
    report_type: PartnerReportTypeEnum
    title: str
    generated_at: datetime
    currency: str
    totals: PartnerReportTotalsDomainModel
    rows: list[PartnerReportRowDomainModel]

    @classmethod
    def from_rows(
        cls,
        *,
        report_type: PartnerReportTypeEnum,
        title: str,
        currency: str,
        rows: list[PartnerReportRowDomainModel],
    ) -> PartnerReportDomainModel:
        return cls(
            report_type=report_type,
            title=title,
            generated_at=datetime.now(tz=UTC),
            currency=currency,
            totals=PartnerReportTotalsDomainModel(
                revenue_amount=round(sum(row.revenue_amount for row in rows), 2),
                currency=currency,
                booking_count=sum(row.booking_count for row in rows),
                lead_count=sum(row.lead_count for row in rows),
                commission_amount=round(sum(row.commission_amount for row in rows), 2),
            ),
            rows=rows,
        )


def mock_partner_report_row(
    *,
    partner_type: PartnerTypeEnum,
    partner_id: str,
    partner_name: str,
    currency: str,
) -> PartnerReportRowDomainModel:
    lead_count = mockutils.random.randint(50, 2500)
    booking_count = mockutils.random.randint(5, lead_count)
    revenue_amount = mockutils.random_booking_amount(50_000.0, 5_000_000.0)
    commission_amount = round(revenue_amount * mockutils.random.uniform(0.02, 0.18), 2)
    return PartnerReportRowDomainModel(
        partner_type=partner_type,
        partner_id=partner_id,
        partner_name=partner_name,
        revenue_amount=revenue_amount,
        currency=currency,
        booking_count=booking_count,
        lead_count=lead_count,
        commission_amount=commission_amount,
        conversion_rate=round((booking_count / lead_count) * 100, 2),
        performance_score=round(mockutils.random.uniform(35.0, 98.0), 2),
    )
