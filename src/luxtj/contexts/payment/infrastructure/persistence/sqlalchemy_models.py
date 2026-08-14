from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.payment.domain.transaction import PaymentGatewayTransaction


class PaymentBase(DeclarativeBase):
    pass


class PaymentGatewayTransactionRow(PaymentBase):
    __tablename__ = "payment_gateway_transactions"
    __table_args__ = (
        UniqueConstraint("transaction_id"),
        Index("ix_payment_gateway_transactions_app_reference", "app_reference"),
        Index("ix_payment_gateway_transactions_pg_code", "pg_code"),
        Index(
            "ix_payment_gateway_transactions_flight_booking_details_id",
            "flight_booking_details_id",
        ),
        Index("ix_payment_gateway_transactions_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    flight_booking_details_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    pg_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    booking_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    request_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pg_reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pg_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    pg_currency_conversion_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8), nullable=True
    )
    pg_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    refund_remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refund_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    refund_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, entity: PaymentGatewayTransaction) -> PaymentGatewayTransactionRow:
        request_params = entity.request_params
        if isinstance(request_params, str):
            request_params = None
        response_params = entity.response_params
        if isinstance(response_params, str):
            response_params = None
        return cls(
            id=str(entity.id),
            transaction_id=entity.transaction_id,
            app_reference=entity.app_reference,
            flight_booking_details_id=entity.flight_booking_details_id,
            pg_code=entity.pg_code,
            status=entity.status,
            amount=entity.amount,
            booking_amount=entity.booking_amount,
            currency=entity.currency,
            request_params=request_params if isinstance(request_params, dict) else None,
            response_params=response_params if isinstance(response_params, dict) else None,
            pg_reference_id=entity.pg_reference_id,
            pg_currency=entity.pg_currency,
            pg_currency_conversion_rate=entity.pg_currency_conversion_rate,
            pg_amount=entity.pg_amount,
            refunded_amount=entity.refunded_amount or Decimal("0"),
            refund_remark=entity.refund_remark,
            refund_mode=entity.refund_mode,
            refund_details=entity.refund_details
            if isinstance(entity.refund_details, dict)
            else None,
            refunded_at=entity.refunded_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_domain(self) -> PaymentGatewayTransaction:
        return PaymentGatewayTransaction(
            id=UUID(self.id),
            transaction_id=self.transaction_id,
            app_reference=self.app_reference,
            pg_code=self.pg_code,
            status=self.status,
            amount=Decimal(str(self.amount)),
            booking_amount=Decimal(str(self.booking_amount)),
            currency=self.currency,
            request_params=self.request_params,
            response_params=self.response_params,
            pg_reference_id=self.pg_reference_id,
            pg_currency=self.pg_currency,
            pg_currency_conversion_rate=(
                None
                if self.pg_currency_conversion_rate is None
                else Decimal(str(self.pg_currency_conversion_rate))
            ),
            pg_amount=None if self.pg_amount is None else Decimal(str(self.pg_amount)),
            flight_booking_details_id=self.flight_booking_details_id,
            refunded_amount=Decimal(str(self.refunded_amount or 0)),
            refund_remark=self.refund_remark,
            refund_mode=self.refund_mode,
            refund_details=self.refund_details if isinstance(self.refund_details, dict) else None,
            refunded_at=self.refunded_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
