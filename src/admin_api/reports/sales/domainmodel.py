from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from luxtj.utils import mockutils


class SalesReportTypeEnum(StrEnum):
    DAILY = "daily_sales"
    MONTHLY = "monthly_sales"
    DESTINATION = "destination_sales"
    PROPERTY = "property_sales"


class SalesPeriodTypeEnum(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    RANGE = "range"


class SalesDimensionTypeEnum(StrEnum):
    OVERALL = "overall"
    DESTINATION = "destination"
    PROPERTY = "property"


@dataclass
class SalesDimensionOptionDomainModel:
    dimension_type: SalesDimensionTypeEnum
    dimension_id: str
    dimension_name: str


@dataclass
class SalesReportRowDomainModel:
    timestamp: date
    period_type: SalesPeriodTypeEnum
    dimension_type: SalesDimensionTypeEnum
    dimension_id: str
    dimension_name: str
    sales_amount: float
    currency: str
    booking_count: int
    units_sold: int

    @property
    def average_order_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.sales_amount / self.booking_count, 2)


@dataclass
class SalesReportTotalsDomainModel:
    sales_amount: float
    currency: str
    booking_count: int
    units_sold: int

    @property
    def average_order_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.sales_amount / self.booking_count, 2)


@dataclass
class SalesReportDomainModel:
    report_type: SalesReportTypeEnum
    title: str
    generated_at: datetime
    currency: str
    totals: SalesReportTotalsDomainModel
    rows: list[SalesReportRowDomainModel]

    @classmethod
    def from_rows(
        cls,
        *,
        report_type: SalesReportTypeEnum,
        title: str,
        currency: str,
        rows: list[SalesReportRowDomainModel],
    ) -> SalesReportDomainModel:
        return cls(
            report_type=report_type,
            title=title,
            generated_at=datetime.now(tz=UTC),
            currency=currency,
            totals=SalesReportTotalsDomainModel(
                sales_amount=round(sum(row.sales_amount for row in rows), 2),
                currency=currency,
                booking_count=sum(row.booking_count for row in rows),
                units_sold=sum(row.units_sold for row in rows),
            ),
            rows=rows,
        )


def mock_sales_report_row(
    *,
    timestamp: date,
    period_type: SalesPeriodTypeEnum,
    dimension_type: SalesDimensionTypeEnum,
    dimension_id: str,
    dimension_name: str,
    currency: str,
) -> SalesReportRowDomainModel:
    booking_count = mockutils.random.randint(12, 420)
    return SalesReportRowDomainModel(
        timestamp=timestamp,
        period_type=period_type,
        dimension_type=dimension_type,
        dimension_id=dimension_id,
        dimension_name=dimension_name,
        sales_amount=mockutils.random_booking_amount(10_000.0, 250_000.0),
        currency=currency,
        booking_count=booking_count,
        units_sold=booking_count + mockutils.random.randint(0, 180),
    )


def date_range_days(
    *, from_date: date | None, to_date: date | None, fallback_days: int
) -> list[date]:
    end_date = to_date or datetime.now(tz=UTC).date()
    start_date = from_date or (end_date - timedelta(days=fallback_days - 1))
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    total_days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=day_index) for day_index in range(total_days)]


def month_range(
    *, from_date: date | None, to_date: date | None, fallback_months: int
) -> list[date]:
    end_date = to_date or datetime.now(tz=UTC).date()
    start_date = from_date or (end_date - timedelta(days=30 * (fallback_months - 1)))
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    months: list[date] = []
    current = date(start_date.year, start_date.month, 1)
    final = date(end_date.year, end_date.month, 1)
    while current <= final:
        months.append(current)
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, 1)
    return months
