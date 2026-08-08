from typing import Any

from pydantic import Field

from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class PaymentTransactionBody(ApiSerializerBaseModel):
    transaction_id: str = Field(..., description="Internal payment transaction id")


class PaymentResponseBody(ApiSerializerBaseModel):
    transaction_id: str = Field(..., description="Internal payment transaction id")
    session_id: str | None = Field(
        None, description="Gateway reference id from return URL (e.g. Razorpay payment id)"
    )


class PaymentStatusBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., description="Booking app_reference correlation key")


class CreatePaymentRecordBody(ApiSerializerBaseModel):
    app_reference: str
    pg_code: str | None = None
    currency: str
    booking_amount: float
    amount: float
    firstname: str
    email: str
    phone: str
    productinfo: str
    flight_booking_details_id: str | None = None


class PaymentInitiateResult(ApiSerializerBaseModel):
    checkout_session_url: str | None = None
    pg_reference_id: str | None = None
    message: str | None = None


class PaymentStatusResult(ApiSerializerBaseModel):
    paid: bool
    message: str | None = None


class PaymentRevalidateBody(ApiSerializerBaseModel):
    transaction_id: str = Field(..., description="Internal payment transaction id")
    pg_reference_id: str | None = Field(
        None, description="Gateway order/session id (e.g. Razorpay order_id)"
    )
    gateway_response: dict[str, Any] | None = Field(
        None,
        description=(
            "Client-side gateway payload used for verification "
            "(e.g. razorpay_payment_id, razorpay_order_id, razorpay_signature)"
        ),
    )


class PaymentRevalidateResult(ApiSerializerBaseModel):
    paid: bool
    fully_paid: bool = False
    app_reference: str | None = None
    transaction_id: str | None = None
    pg_code: str | None = None
    paid_amount: float | None = None
    message: str | None = None


class CreatePaymentRecordResult(ApiSerializerBaseModel):
    transaction_id: str
    payment_url: str
    pg_code: str | None = None
    pg_reference_id: str | None = None
    payment: dict[str, Any] | None = None
