from dataclasses import dataclass
from datetime import datetime

from admin_api.customer.users.domainmodel import CustomerDomainModel
from luxtj.domain.enums import (
    BookingSourceEnum,
    BookingStatusEnum,
    BookingTypeEnum,
    PaymentStatusEnum,
    RefundStatusEnum,
)
from luxtj.utils import mockutils


@dataclass
class BookingBizKpiSummaryDomainModel:
    amount_currency: str
    total_bookings: int
    total_booking_value: float
    net_revenue: float
    amount_currency: str
    payment_success_rate: float
    cancellation_rate: float
    refund_rate: float

    @classmethod
    def generate_mock(cls, *, mock_currency: str) -> BookingBizKpiSummaryDomainModel:
        return cls(
            amount_currency=mock_currency,
            total_bookings=mockutils.random.randint(100, 1000),
            total_booking_value=mockutils.random_booking_amount(10000.0, 100000.0),
            net_revenue=mockutils.random_booking_amount(5000.0, 90000.0),
            payment_success_rate=mockutils.random.uniform(0.8, 1.0),
            cancellation_rate=mockutils.random.uniform(0.0, 0.2),
            refund_rate=mockutils.random.uniform(0.0, 0.1),
        )


@dataclass
class CustomerBookingDomainModel:
    booking_id: str
    customer: CustomerDomainModel
    booking_type: BookingTypeEnum
    booking_created_at: datetime
    travel_start_at: datetime
    booking_status: BookingStatusEnum
    booking_total_amount: float
    amount_currency: str
    booking_paid_amount: float
    payment_status: PaymentStatusEnum
    refund_status: RefundStatusEnum
    origin_location: str
    destination_location: str
    booking_source: BookingSourceEnum

    @classmethod
    def generate_mock(cls, *, mock_currency: str) -> CustomerBookingDomainModel:
        return cls(
            booking_id="b1",
            customer=CustomerDomainModel.generate_mock(mock_currency=mock_currency),
            booking_type=mockutils.random.choice(list(BookingTypeEnum)),
            booking_created_at=mockutils.random_registration_date(),
            travel_start_at=mockutils.random_registration_date(),
            booking_status=mockutils.random.choice(list(BookingStatusEnum)),
            booking_total_amount=mockutils.random_booking_amount(100.0, 1000.0),
            amount_currency=mock_currency,
            booking_paid_amount=mockutils.random_booking_amount(50.0, 1000.0),
            payment_status=mockutils.random.choice(list(PaymentStatusEnum)),
            refund_status=mockutils.random.choice(list(RefundStatusEnum)),
            origin_location=mockutils.random_user_base_location(),
            destination_location=mockutils.random_user_base_location(),
            booking_source=mockutils.random.choice(list(BookingSourceEnum)),
        )
