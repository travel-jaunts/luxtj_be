from dataclasses import dataclass
from datetime import datetime

from luxtj.domain.enums import CustomerStatusEnum, CustomerTierEnum
from luxtj.utils import mockutils


@dataclass
class CustomerBizKpiSummaryDomainModel:
    amount_currency: str
    total_revenue: float
    average_order_value: float
    total_customers: int
    active_customers: int
    repeat_rate: float
    cancellation_rate: float
    customers_by_tier: dict[CustomerTierEnum, int]

    @classmethod
    def generate_mock(cls, *, mock_currency: str = "INR") -> CustomerBizKpiSummaryDomainModel:
        return cls(
            amount_currency=mock_currency,
            total_revenue=mockutils.random_booking_amount(10000, 1000000),
            average_order_value=mockutils.random_booking_amount(50, 500),
            total_customers=mockutils.random.randint(100, 10000),
            active_customers=mockutils.random.randint(50, 5000),
            repeat_rate=mockutils.random.uniform(0, 100),
            cancellation_rate=mockutils.random.uniform(0, 100),
            customers_by_tier={
                tier: mockutils.random.randint(0, 1000) for tier in CustomerTierEnum
            },
        )


@dataclass
class CustomerDomainModel:
    user_id: str
    user_amount_currency: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_phone_number: str
    user_base_location: str
    user_registration_date: datetime  # ISO format date string
    user_last_booking_date: datetime | None  # ISO format date string, can be null
    user_total_spend: float
    user_booking_count: int
    user_average_order_value: float
    user_cancellation_count: int
    user_is_active: bool
    user_tier: CustomerTierEnum
    user_status: CustomerStatusEnum

    @property
    def user_cancellation_rate(self) -> float:
        if self.user_booking_count == 0:
            return 0.0
        return (self.user_cancellation_count / self.user_booking_count) * 100

    @classmethod
    def generate_mock(cls, *, mock_currency: str = "INR") -> CustomerDomainModel:
        is_user_active: bool = mockutils.random.choice([True, False])
        return cls(
            user_id=mockutils.random_user_id(),
            user_amount_currency=mock_currency,
            user_first_name=mockutils.random_user_first_name(),
            user_last_name=mockutils.random_user_last_name(),
            user_email=mockutils.random_user_email(),
            user_phone_number=mockutils.random_user_phone_number(),
            user_base_location=mockutils.random_user_base_location(),
            user_registration_date=mockutils.random_registration_date(),
            user_last_booking_date=mockutils.random_registration_date(),
            user_total_spend=mockutils.random_booking_amount(100, 10000),
            user_booking_count=mockutils.random.randint(1, 50),
            user_average_order_value=mockutils.random_booking_amount(50, 500),
            user_cancellation_count=mockutils.random.randint(0, 10),
            user_is_active=is_user_active,
            user_tier=CustomerTierEnum.NOVUS,
            user_status=CustomerStatusEnum.ACTIVE
            if is_user_active
            else CustomerStatusEnum.INACTIVE,
        )
