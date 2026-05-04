from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from admin_api.customer.users.domainmodel import CustomerDomainModel
from luxtj.utils import mockutils


class CustomerSpendCategoryEnum(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VIP = "vip"


@dataclass
class CustomerReportIdentityDomainModel:
    customer_id: str
    customer_name: str
    email: str
    phone_number: str

    @classmethod
    def from_customer_model(
        cls, customer_model: CustomerDomainModel
    ) -> CustomerReportIdentityDomainModel:
        return cls(
            customer_id=customer_model.user_id,
            customer_name=(
                f"{customer_model.user_first_name} {customer_model.user_last_name}".strip()
            ),
            email=customer_model.user_email,
            phone_number=customer_model.user_phone_number,
        )


@dataclass
class CustomerOverviewDomainModel:
    title: str
    generated_at: datetime
    currency: str
    from_date: date | None
    to_date: date | None
    total_customers: int
    new_customers: int
    active_customers: int
    average_booking_value: float


@dataclass
class CustomerValueRowDomainModel:
    customer: CustomerReportIdentityDomainModel
    lifetime_value: float
    revenue_amount: float
    currency: str
    booking_count: int
    spend_category: CustomerSpendCategoryEnum

    @property
    def revenue_per_customer(self) -> float:
        return self.revenue_amount

    @property
    def average_booking_value(self) -> float:
        if self.booking_count == 0:
            return 0.0
        return round(self.revenue_amount / self.booking_count, 2)

    @property
    def is_high_value_customer(self) -> bool:
        return self.spend_category in {
            CustomerSpendCategoryEnum.HIGH,
            CustomerSpendCategoryEnum.VIP,
        }


@dataclass
class CustomerValueTotalsDomainModel:
    customer_count: int
    lifetime_value: float
    revenue_amount: float
    currency: str
    high_value_customer_count: int
    customers_by_spend_category: dict[CustomerSpendCategoryEnum, int]

    @property
    def revenue_per_customer(self) -> float:
        if self.customer_count == 0:
            return 0.0
        return round(self.revenue_amount / self.customer_count, 2)


@dataclass
class CustomerValueReportDomainModel:
    title: str
    generated_at: datetime
    currency: str
    totals: CustomerValueTotalsDomainModel
    rows: list[CustomerValueRowDomainModel]

    @classmethod
    def from_rows(
        cls,
        *,
        currency: str,
        rows: list[CustomerValueRowDomainModel],
    ) -> CustomerValueReportDomainModel:
        customers_by_spend_category = dict.fromkeys(CustomerSpendCategoryEnum, 0)
        for row in rows:
            customers_by_spend_category[row.spend_category] += 1

        return cls(
            title="Customer Value",
            generated_at=datetime.now(tz=UTC),
            currency=currency,
            totals=CustomerValueTotalsDomainModel(
                customer_count=len(rows),
                lifetime_value=round(sum(row.lifetime_value for row in rows), 2),
                revenue_amount=round(sum(row.revenue_amount for row in rows), 2),
                currency=currency,
                high_value_customer_count=sum(1 for row in rows if row.is_high_value_customer),
                customers_by_spend_category=customers_by_spend_category,
            ),
            rows=rows,
        )


@dataclass
class CustomerSatisfactionReportDomainModel:
    title: str
    generated_at: datetime
    customer: CustomerReportIdentityDomainModel
    average_rating: float
    rating_count: int
    review_count: int
    complaint_count: int
    support_ticket_count: int
    open_support_ticket_count: int
    average_support_resolution_hours: float


def mock_customer_overview(
    *,
    currency: str,
    from_date: date | None,
    to_date: date | None,
) -> CustomerOverviewDomainModel:
    total_customers = mockutils.random.randint(3_000, 50_000)
    new_customers = mockutils.random.randint(100, max(100, total_customers // 8))
    active_customers = mockutils.random.randint(total_customers // 3, total_customers)
    return CustomerOverviewDomainModel(
        title="Customer Overview",
        generated_at=datetime.now(tz=UTC),
        currency=currency,
        from_date=from_date,
        to_date=to_date,
        total_customers=total_customers,
        new_customers=new_customers,
        active_customers=active_customers,
        average_booking_value=mockutils.random_booking_amount(25_000.0, 250_000.0),
    )


def mock_customer_value_row(
    *,
    customer: CustomerReportIdentityDomainModel,
    currency: str,
) -> CustomerValueRowDomainModel:
    spend_category = mockutils.random.choice(list(CustomerSpendCategoryEnum))
    booking_count = mockutils.random.randint(1, 48)
    revenue_amount = mockutils.random_booking_amount(15_000.0, 2_500_000.0)
    lifetime_value = round(revenue_amount * mockutils.random.uniform(1.05, 2.5), 2)
    return CustomerValueRowDomainModel(
        customer=customer,
        lifetime_value=lifetime_value,
        revenue_amount=revenue_amount,
        currency=currency,
        booking_count=booking_count,
        spend_category=spend_category,
    )
