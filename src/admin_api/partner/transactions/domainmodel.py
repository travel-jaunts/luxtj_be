from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from luxtj.utils import mockutils


class PartnerPaymentStatusEnum(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    RELEASED = "released"
    HOLD = "hold"
    REFUND = "refund"


class PartnerRefundStatusEnum(StrEnum):
    INITIATED = "initiated"
    APPROVED = "approved"
    PROCESSED = "processed"
    REJECTED = "rejected"


class PartnerPaymentTypeEnum(StrEnum):
    COMMISSION = "commission"
    INCENTIVE = "incentive"
    ADJUSTMENT = "adjustment"


@dataclass
class PartnerTransactionsSummaryDomainModel:
    total_partner_payments_amount: float
    pending_payments_amount: float
    refunds_pending_amount: float
    completed_payments_amount: float
    amount_currency: str

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str) -> PartnerTransactionsSummaryDomainModel:
        total_partner_payments_amount = mockutils.random_booking_amount(50000.0, 5000000.0)
        pending_payments_amount = mockutils.random_booking_amount(0.0, 1000000.0)
        refunds_pending_amount = mockutils.random_booking_amount(0.0, 200000.0)
        completed_payments_amount = max(
            0.0,
            round(
                total_partner_payments_amount - pending_payments_amount - refunds_pending_amount, 2
            ),
        )

        return cls(
            total_partner_payments_amount=total_partner_payments_amount,
            pending_payments_amount=pending_payments_amount,
            refunds_pending_amount=refunds_pending_amount,
            completed_payments_amount=completed_payments_amount,
            amount_currency=iso_currency_str,
        )


@dataclass
class PartnerPaymentLineItemDomainModel:
    payment_id: str
    partner: str
    payment_type: PartnerPaymentTypeEnum
    amount: float
    currency: str
    booking_id: str
    status: PartnerPaymentStatusEnum
    date: datetime

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str) -> PartnerPaymentLineItemDomainModel:
        return cls(
            payment_id=mockutils.random_transaction_id(),
            partner=f"{mockutils.random_user_last_name()} Travels",
            payment_type=mockutils.random.choice(list(PartnerPaymentTypeEnum)),
            amount=mockutils.random_booking_amount(1000.0, 250000.0),
            currency=iso_currency_str,
            booking_id=mockutils.random_booking_id(),
            status=mockutils.random.choice(list(PartnerPaymentStatusEnum)),
            date=mockutils.random_date_from_past_days(),
        )


@dataclass
class PartnerRefundLineItemDomainModel:
    refund_id: str
    booking: str
    customer: str
    amount: float
    currency: str
    reason: str
    status: PartnerRefundStatusEnum

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str) -> PartnerRefundLineItemDomainModel:
        reasons = [
            "Customer cancellation",
            "Duplicate payment",
            "Inventory mismatch",
            "Price correction",
            "Service quality issue",
        ]
        customer = f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}"
        return cls(
            refund_id=mockutils.random_transaction_id(),
            booking=mockutils.random_booking_id(),
            customer=customer,
            amount=mockutils.random_booking_amount(500.0, 100000.0),
            currency=iso_currency_str,
            reason=mockutils.random.choice(reasons),
            status=mockutils.random.choice(list(PartnerRefundStatusEnum)),
        )
