from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from admin_api.customer.users.domainmodel import CustomerDomainModel
from luxtj.utils import mockutils


class BookingReportTypeEnum(StrEnum):
    OVERVIEW = "booking_overview"
    CANCELLATIONS = "cancellations"


class BookingReportGroupByEnum(StrEnum):
    DAY = "day"
    MONTH = "month"
    CUSTOMER = "customer"


@dataclass
class BookingReportCustomerOptionDomainModel:
    customer_id: str
    customer_name: str
    email: str
    phone_number: str

    @classmethod
    def from_customer_model(
        cls, customer_model: CustomerDomainModel
    ) -> BookingReportCustomerOptionDomainModel:
        return cls(
            customer_id=customer_model.user_id,
            customer_name=(
                f"{customer_model.user_first_name} {customer_model.user_last_name}".strip()
            ),
            email=customer_model.user_email,
            phone_number=customer_model.user_phone_number,
        )


@dataclass
class BookingReportRowDomainModel:
    group_by: BookingReportGroupByEnum
    label: str
    period_start: date | None
    customer: BookingReportCustomerOptionDomainModel | None
    booking_count: int
    cancellation_count: int
    gross_booking_amount: float
    cancelled_amount: float
    currency: str

    @property
    def net_booking_amount(self) -> float:
        return round(self.gross_booking_amount - self.cancelled_amount, 2)

    @property
    def average_booking_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.gross_booking_amount / self.booking_count, 2)

    @property
    def cancellation_rate(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round((self.cancellation_count / self.booking_count) * 100, 2)


@dataclass
class BookingReportTotalsDomainModel:
    booking_count: int
    cancellation_count: int
    gross_booking_amount: float
    cancelled_amount: float
    currency: str

    @property
    def net_booking_amount(self) -> float:
        return round(self.gross_booking_amount - self.cancelled_amount, 2)

    @property
    def average_booking_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.gross_booking_amount / self.booking_count, 2)

    @property
    def cancellation_rate(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round((self.cancellation_count / self.booking_count) * 100, 2)


@dataclass
class BookingReportDomainModel:
    report_type: BookingReportTypeEnum
    group_by: BookingReportGroupByEnum
    title: str
    generated_at: datetime
    currency: str
    totals: BookingReportTotalsDomainModel
    rows: list[BookingReportRowDomainModel]

    @classmethod
    def from_rows(
        cls,
        *,
        report_type: BookingReportTypeEnum,
        group_by: BookingReportGroupByEnum,
        title: str,
        currency: str,
        rows: list[BookingReportRowDomainModel],
    ) -> BookingReportDomainModel:
        return cls(
            report_type=report_type,
            group_by=group_by,
            title=title,
            generated_at=datetime.now(tz=UTC),
            currency=currency,
            totals=BookingReportTotalsDomainModel(
                booking_count=sum(row.booking_count for row in rows),
                cancellation_count=sum(row.cancellation_count for row in rows),
                gross_booking_amount=round(sum(row.gross_booking_amount for row in rows), 2),
                cancelled_amount=round(sum(row.cancelled_amount for row in rows), 2),
                currency=currency,
            ),
            rows=rows,
        )


def report_date_range(
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


def day_points(*, from_date: date, to_date: date, max_points: int) -> list[date]:
    total_days = (to_date - from_date).days + 1
    if total_days <= max_points:
        return [from_date + timedelta(days=day_index) for day_index in range(total_days)]

    step_days = max(1, total_days // max_points)
    points = [
        from_date + timedelta(days=day_index) for day_index in range(0, total_days, step_days)
    ]
    return [*points[: max_points - 1], to_date]


def month_points(*, from_date: date, to_date: date) -> list[date]:
    months: list[date] = []
    current = date(from_date.year, from_date.month, 1)
    final = date(to_date.year, to_date.month, 1)
    while current <= final:
        months.append(current)
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, 1)
    return months


def mock_booking_report_row(
    *,
    group_by: BookingReportGroupByEnum,
    label: str,
    period_start: date | None,
    customer: BookingReportCustomerOptionDomainModel | None,
    currency: str,
) -> BookingReportRowDomainModel:
    booking_count = mockutils.random.randint(12, 450)
    cancellation_count = mockutils.random.randint(0, max(1, booking_count // 4))
    gross_booking_amount = mockutils.random_booking_amount(25_000.0, 1_200_000.0)
    cancelled_amount = round(
        gross_booking_amount * mockutils.random.uniform(0.0, 0.18),
        2,
    )
    return BookingReportRowDomainModel(
        group_by=group_by,
        label=label,
        period_start=period_start,
        customer=customer,
        booking_count=booking_count,
        cancellation_count=cancellation_count,
        gross_booking_amount=gross_booking_amount,
        cancelled_amount=cancelled_amount,
        currency=currency,
    )
