"""Payment gateway transaction ledger entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from luxtj.utils import timeutils


@dataclass
class PaymentGatewayTransaction:
    id: UUID
    transaction_id: str
    app_reference: str
    pg_code: str
    status: str
    amount: Decimal
    booking_amount: Decimal
    currency: str
    request_params: dict | str | None
    response_params: dict | str | None
    pg_reference_id: str | None
    pg_currency: str | None
    pg_currency_conversion_rate: Decimal | None
    pg_amount: Decimal | None
    flight_booking_details_id: str | None
    refunded_amount: Decimal
    refund_remark: str | None
    refund_mode: str | None
    refund_details: dict | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_pending(
        cls,
        *,
        transaction_id: str,
        app_reference: str,
        pg_code: str,
        amount: Decimal,
        booking_amount: Decimal,
        currency: str,
        request_params: dict,
        pg_currency_conversion_rate: Decimal,
        flight_booking_details_id: str | None = None,
        now: datetime | None = None,
    ) -> PaymentGatewayTransaction:
        ts = now or timeutils.datetime_now()
        return cls(
            id=uuid4(),
            transaction_id=transaction_id,
            app_reference=app_reference,
            pg_code=pg_code,
            status="pending",
            amount=amount,
            booking_amount=booking_amount,
            currency=currency,
            request_params=request_params,
            response_params=None,
            pg_reference_id=transaction_id,
            pg_currency=currency,
            pg_currency_conversion_rate=pg_currency_conversion_rate,
            pg_amount=amount,
            flight_booking_details_id=flight_booking_details_id,
            refunded_amount=Decimal("0"),
            refund_remark=None,
            refund_mode=None,
            refund_details=None,
            refunded_at=None,
            created_at=ts,
            updated_at=ts,
        )

    def is_accepted(self) -> bool:
        return self.status.lower() == "accepted"

    def is_pending(self) -> bool:
        return self.status.lower() == "pending"

    def refundable_amount(self) -> Decimal:
        paid = Decimal(str(self.amount or 0))
        already = Decimal(str(self.refunded_amount or 0))
        remaining = paid - already
        return remaining if remaining > 0 else Decimal("0")
