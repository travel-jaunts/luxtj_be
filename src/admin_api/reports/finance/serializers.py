from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, Field

from admin_api.reports.finance.domainmodel import (
    FinanceMetricDomainModel,
    FinanceMetricTypeEnum,
    FinanceReportDomainModel,
    FinanceTrendPointDomainModel,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class FinanceReportQuery(ApiSerializerBaseModel):
    from_date: date | None = Field(None, description="Start date for the finance overview")
    to_date: date | None = Field(None, description="End date for the finance overview")


class FinanceMetric(ApiSerializerBaseModel):
    metric_type: FinanceMetricTypeEnum
    title: str
    amount: AmountSerializer
    transaction_count: int
    previous_amount: AmountSerializer
    change_percent: float

    @classmethod
    def from_domain_model(cls, domain_model: FinanceMetricDomainModel) -> FinanceMetric:
        return cls(
            metric_type=domain_model.metric_type,
            title=domain_model.title,
            amount=AmountSerializer(
                amount=domain_model.amount,
                currency=domain_model.currency,
            ),
            transaction_count=domain_model.transaction_count,
            previous_amount=AmountSerializer(
                amount=domain_model.previous_amount,
                currency=domain_model.currency,
            ),
            change_percent=domain_model.change_percent,
        )


class FinanceTrendPoint(ApiSerializerBaseModel):
    timestamp: date
    revenue: AmountSerializer
    payments: AmountSerializer
    refunds: AmountSerializer
    profit: AmountSerializer

    @classmethod
    def from_domain_model(cls, domain_model: FinanceTrendPointDomainModel) -> FinanceTrendPoint:
        return cls(
            timestamp=domain_model.timestamp,
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.currency,
            ),
            payments=AmountSerializer(
                amount=domain_model.payments_amount,
                currency=domain_model.currency,
            ),
            refunds=AmountSerializer(
                amount=domain_model.refunds_amount,
                currency=domain_model.currency,
            ),
            profit=AmountSerializer(
                amount=domain_model.profit_amount,
                currency=domain_model.currency,
            ),
        )


class FinanceReport(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    currency: str
    from_date: date
    to_date: date
    metrics: list[FinanceMetric]
    # trend: list[FinanceTrendPoint]

    @classmethod
    def from_domain_model(cls, domain_model: FinanceReportDomainModel) -> FinanceReport:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            from_date=domain_model.from_date,
            to_date=domain_model.to_date,
            metrics=[FinanceMetric.from_domain_model(metric) for metric in domain_model.metrics],
            # trend=[FinanceTrendPoint.from_domain_model(point) for point in domain_model.trend],
        )
