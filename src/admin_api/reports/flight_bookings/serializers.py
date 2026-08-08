"""Admin flight booking report serializers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class FlightBookingListFilters(ApiSerializerBaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="pageSize")
    status: str | None = Field(
        None,
        description="Booking status filter; omit or 'all' for every status",
    )
    email: str | None = None
    booking_no: str | None = Field(None, alias="bookingNo")
    airline: str | None = None
    from_date: date | None = Field(None, alias="fromDate")
    to_date: date | None = Field(None, alias="toDate")


class JourneySummarySerializer(ApiSerializerBaseModel):
    airline_code: str | None = None
    origin: str | None = None
    destination: str | None = None
    stops: int = 0
    origin_label: str | None = None
    destination_label: str | None = None


class FlightBookingListItemSerializer(ApiSerializerBaseModel):
    app_reference: str
    status: str
    payment_status: str
    booking_source: str
    gdspnr: str | None = None
    booking_id: str | None = None
    trip_type: str
    cabin_class: str | None = None
    origin: str | None = None
    destination: str | None = None
    departure_date: str | None = None
    return_date: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_passenger_name: str | None = None
    passenger_count: int = 0
    journeys: list[JourneySummarySerializer] = Field(default_factory=list)
    total_fare: float | None = None
    currency: str | None = None
    payment_mode: str | None = None
    created_at: datetime


class FlightBookingListResultSerializer(ApiSerializerBaseModel):
    total: int
    page: int
    page_size: int
    items: list[FlightBookingListItemSerializer]


class FlightBookingDetailsBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., alias="appReference", min_length=1)


class FlightBookingRefreshBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., alias="appReference", min_length=1)


class PricingLineSerializer(ApiSerializerBaseModel):
    label: str
    admin_amount: float
    booked_amount: float | None = None


class PassengerDetailSerializer(ApiSerializerBaseModel):
    title: str | None = None
    first_name: str = ""
    last_name: str = ""
    age_type: str = "Adult"
    date_of_birth: str | None = None
    gender: str | None = None
    nationality: str | None = None
    document_number: str | None = None
    document_expiry: str | None = None
    ticket_number: str | None = None
    attributes: dict[str, Any] | None = None


class SegmentDetailSerializer(ApiSerializerBaseModel):
    airline_code: str | None = None
    flight_number: str | None = None
    origin: str | None = None
    destination: str | None = None
    departure_datetime: str | None = None
    arrival_datetime: str | None = None
    cabin_class: str | None = None
    pnr: str | None = None
    rph: int = 1


class ExtraServiceLineSerializer(ApiSerializerBaseModel):
    passenger_name: str
    age_type: str
    item_type: str
    segment: str | None = None
    detail: str | None = None
    price: float | None = None
    currency: str | None = None


class PaymentTxnSerializer(ApiSerializerBaseModel):
    gateway: str
    status: str
    amount: float
    currency: str
    pg_amount: float | None = None
    pg_currency: str | None = None
    reference: str | None = None
    transaction_id: str


class PricingBlockSerializer(ApiSerializerBaseModel):
    admin_currency: str
    booked_currency: str | None = None
    conversion_rate: float | None = None
    lines: list[PricingLineSerializer] = Field(default_factory=list)
    total_fare_admin: float
    total_fare_booked: float | None = None
    excess_baggage_total: float | None = None


class FlightBookingDetailSerializer(ApiSerializerBaseModel):
    app_reference: str
    status: str
    payment_status: str
    booking_source: str
    booking_id: str | None = None
    book_guid: str | None = None
    gdspnr: str | None = None
    trip_type: str
    cabin_class: str | None = None
    origin: str | None = None
    destination: str | None = None
    departure_date: str | None = None
    return_date: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_passenger_name: str | None = None
    created_at: datetime
    updated_at: datetime
    route_summary: str | None = None
    passengers: list[PassengerDetailSerializer] = Field(default_factory=list)
    segments: list[SegmentDetailSerializer] = Field(default_factory=list)
    journeys: list[JourneySummarySerializer] = Field(default_factory=list)
    extras: list[ExtraServiceLineSerializer] = Field(default_factory=list)
    pricing: PricingBlockSerializer | None = None
    payments: list[PaymentTxnSerializer] = Field(default_factory=list)
    attributes: dict[str, Any] | None = None
    details_snapshot: dict[str, Any] | None = None
