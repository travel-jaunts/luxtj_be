from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from luxtj.utils import mockutils


class FinanceMetricTypeEnum(StrEnum):
    REVENUE = "revenue"
    PAYMENTS = "payments"
    REFUNDS = "refunds"
    PROFIT = "profit"


@dataclass
class FinanceMetricDomainModel:
    metric_type: FinanceMetricTypeEnum
    title: str
    amount: float
    currency: str
    transaction_count: int
    previous_amount: float

    @property
    def change_percent(self) -> float:
        if self.previous_amount == 0:
            return 0.0
        return round(((self.amount - self.previous_amount) / self.previous_amount) * 100, 2)


@dataclass
class FinanceTrendPointDomainModel:
    timestamp: date
    revenue_amount: float
    payments_amount: float
    refunds_amount: float
    profit_amount: float
    currency: str


@dataclass
class FinanceReportDomainModel:
    title: str
    generated_at: datetime
    currency: str
    from_date: date
    to_date: date
    metrics: list[FinanceMetricDomainModel]
    trend: list[FinanceTrendPointDomainModel]


def default_finance_date_range(
    *,
    from_date: date | None,
    to_date: date | None,
    fallback_days: int,
) -> tuple[date, date]:
    end_date = to_date or datetime.now(tz=UTC).date()
    start_date = from_date or (end_date - timedelta(days=fallback_days - 1))
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def finance_trend_dates(*, from_date: date, to_date: date, max_points: int) -> list[date]:
    total_days = (to_date - from_date).days + 1
    if total_days <= max_points:
        return [from_date + timedelta(days=day_index) for day_index in range(total_days)]

    step_days = max(1, total_days // max_points)
    trend_dates = [
        from_date + timedelta(days=day_index) for day_index in range(0, total_days, step_days)
    ]
    return [*trend_dates[: max_points - 1], to_date]


def mock_finance_trend_point(*, timestamp: date, currency: str) -> FinanceTrendPointDomainModel:
    revenue_amount = mockutils.random_booking_amount(100_000.0, 1_500_000.0)
    payments_amount = mockutils.random_booking_amount(revenue_amount * 0.75, revenue_amount)
    refunds_amount = mockutils.random_booking_amount(0.0, revenue_amount * 0.12)
    operating_cost = mockutils.random_booking_amount(revenue_amount * 0.35, revenue_amount * 0.65)
    return FinanceTrendPointDomainModel(
        timestamp=timestamp,
        revenue_amount=revenue_amount,
        payments_amount=payments_amount,
        refunds_amount=refunds_amount,
        profit_amount=round(revenue_amount - refunds_amount - operating_cost, 2),
        currency=currency,
    )


def finance_metric_from_amount(
    *,
    metric_type: FinanceMetricTypeEnum,
    title: str,
    amount: float,
    currency: str,
    transaction_count: int,
) -> FinanceMetricDomainModel:
    previous_amount = round(amount * mockutils.random.uniform(0.8, 1.2), 2)
    return FinanceMetricDomainModel(
        metric_type=metric_type,
        title=title,
        amount=round(amount, 2),
        currency=currency,
        transaction_count=transaction_count,
        previous_amount=previous_amount,
    )
