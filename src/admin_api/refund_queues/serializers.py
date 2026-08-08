"""Admin flight refund queue serializers."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class FlightRefundQueueListBody(ApiSerializerBaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="pageSize")
    search: str | None = None
    booking_status: str | None = Field(None, alias="bookingStatus")


class FlightRefundQueueItemSerializer(ApiSerializerBaseModel):
    app_reference: str
    booking_status: str
    booking_source: str
    email: str | None = None
    phone: str | None = None
    lead_passenger_name: str | None = None
    origin: str | None = None
    destination: str | None = None
    trip_type: str | None = None
    booking_created_at: datetime
    transaction_id: str
    pg_code: str
    payment_status: str
    paid_amount: float
    refunded_amount: float
    refundable_amount: float
    currency: str
    supports_refund_api: bool
    refund_api: str
    payment_created_at: datetime


class FlightRefundQueueListResultSerializer(ApiSerializerBaseModel):
    total: int
    page: int
    page_size: int
    items: list[FlightRefundQueueItemSerializer]


class FlightRefundIssueBody(ApiSerializerBaseModel):
    transaction_id: str = Field(..., alias="transactionId", min_length=1)
    refund_amount: float = Field(..., alias="refundAmount", gt=0)
    remark: str | None = None
    manual_details: str | None = Field(None, alias="manualDetails")


class FlightRefundIssueResultSerializer(ApiSerializerBaseModel):
    transaction_id: str
    app_reference: str
    payment_status: str
    refund_mode: str
    refunded_amount: float
    refund_amount_this_request: float
    currency: str
    supports_refund_api: bool
    message: str
