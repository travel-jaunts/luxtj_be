from dataclasses import dataclass
from datetime import datetime

from admin_api.customer.bookings.domainmodel import CustomerDomainModel

from luxtj.domain.enums import (
    TransactionTypeEnum,
    PaymentMethodEnum,
    PaymentStatusEnum,
    PaymentSourceEnum,
)
from luxtj.utils import mockutils


@dataclass
class PaymentRefundKpiSummaryDomainModel:
    amount_currency: str
    gross_booking_value: float
    total_payments_received: int
    total_refunds_issued: int
    net_revenue: float  # collected - refunds
    outstanding_receivables: float  # amount that is yet to be collected from customers
    reconciliation_accuracy_rate: (
        float  # percentage of payments that are correctly reconciled in the system
    )
    unsuccessfull_payments_count: int  # number of payments that failed due to various reasons (e.g. card declined, insufficient funds, etc.)

    @classmethod
    def generate_mock(cls, *, mock_currency: str) -> "PaymentRefundKpiSummaryDomainModel":
        return cls(
            amount_currency=mock_currency,
            gross_booking_value=mockutils.random_booking_amount(10000.0, 100000.0),
            total_payments_received=mockutils.random.randint(100, 1000),
            total_refunds_issued=mockutils.random.randint(0, 100),
            net_revenue=mockutils.random_booking_amount(5000.0, 90000.0),
            outstanding_receivables=mockutils.random_booking_amount(1000.0, 5000.0),
            reconciliation_accuracy_rate=mockutils.random.uniform(0.8, 1.0),
            unsuccessfull_payments_count=mockutils.random.randint(0, 50),
        )


@dataclass
class CustomerPaymentDomainModel:
    transaction_id: str
    transaction_currency: str
    transaction_amount: float
    customer: CustomerDomainModel
    booking_id: str | None
    transaction_type: TransactionTypeEnum
    transaction_method: PaymentMethodEnum
    transaction_status: PaymentStatusEnum
    transaction_timestamp: datetime
    transaction_source: PaymentSourceEnum
    transaction_source_reference: str

    @classmethod
    def generate_mock(cls, *, mock_currency: str) -> "CustomerPaymentDomainModel":
        return cls(
            transaction_id=mockutils.random_transaction_id(),
            transaction_currency=mock_currency,
            transaction_amount=mockutils.random_booking_amount(100.0, 10000.0),
            customer=CustomerDomainModel.generate_mock(),
            booking_id=mockutils.random_booking_id(),
            transaction_type=mockutils.random.choice(
                [TransactionTypeEnum.PAYMENT, TransactionTypeEnum.REFUND]
            ),
            transaction_method=mockutils.random.choice(
                [
                    PaymentMethodEnum.CREDIT_CARD,
                    PaymentMethodEnum.DEBIT_CARD,
                    PaymentMethodEnum.NET_BANKING,
                    PaymentMethodEnum.WALLET,
                ]
            ),
            transaction_status=mockutils.random.choice(
                [PaymentStatusEnum.COMPLETED, PaymentStatusEnum.FAILED, PaymentStatusEnum.REFUNDED]
            ),
            transaction_timestamp=mockutils.random_registration_date(),
            transaction_source=mockutils.random.choice(
                [PaymentSourceEnum.STRIPE, PaymentSourceEnum.PAYPAL, PaymentSourceEnum.RAZORPAY]
            ),
            transaction_source_reference=mockutils.random_transaction_id(),
        )
