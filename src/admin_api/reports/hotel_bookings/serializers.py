"""Admin hotel booking report serializers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class HotelBookingListFilters(ApiSerializerBaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="pageSize")
    status: str | None = Field(
        None,
        description="Booking status filter; omit or 'all' for every status",
    )
    email: str | None = None
    booking_no: str | None = Field(None, alias="bookingNo")
    hotel: str | None = None
    from_date: date | None = Field(None, alias="fromDate")
    to_date: date | None = Field(None, alias="toDate")


class HotelBookingListItemSerializer(ApiSerializerBaseModel):
    app_reference: str
    status: str
    payment_status: str
    booking_source: str
    booking_reference: str | None = None
    confirmation_reference: str | None = None
    hotel_name: str = ""
    hotel_code: str | None = None
    hotel_location: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    rooms: int = 1
    total_adults: int = 0
    total_children: int = 0
    email: str | None = None
    phone: str | None = None
    lead_guest_name: str | None = None
    guest_count: int = 0
    room_summary: str | None = None
    total_fare: float | None = None
    currency: str | None = None
    payment_mode: str | None = None
    created_at: datetime


class HotelBookingListResultSerializer(ApiSerializerBaseModel):
    total: int
    page: int
    page_size: int
    items: list[HotelBookingListItemSerializer]


class HotelBookingDetailsBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., alias="appReference", min_length=1)


class HotelBookingRefreshBody(ApiSerializerBaseModel):
    app_reference: str = Field(..., alias="appReference", min_length=1)


class PricingLineSerializer(ApiSerializerBaseModel):
    label: str
    admin_amount: float
    booked_amount: float | None = None


class GuestDetailSerializer(ApiSerializerBaseModel):
    title: str | None = None
    first_name: str = ""
    last_name: str = ""
    pax_type: str = "Adult"
    email: str | None = None
    phone: str | None = None
    phone_code: str | None = None


class RoomDetailSerializer(ApiSerializerBaseModel):
    room_type_name: str | None = None
    status: str = ""
    adults: int = 0
    children: int = 0
    base_fare: float = 0
    taxes: float = 0
    hotel_crs_room_code: str | None = None


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


class HotelBookingDetailSerializer(ApiSerializerBaseModel):
    app_reference: str
    status: str
    payment_status: str
    booking_source: str
    booking_reference: str | None = None
    confirmation_reference: str | None = None
    hotel_name: str = ""
    hotel_address: str | None = None
    hotel_location: str | None = None
    hotel_image: str | None = None
    star_rating: int | None = None
    hotel_code: str | None = None
    hotel_crs_hotel_code: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    check_in_time: str | None = None
    check_out_time: str | None = None
    rooms: int = 1
    total_adults: int = 0
    total_children: int = 0
    email: str | None = None
    phone: str | None = None
    lead_guest_name: str | None = None
    created_at: datetime
    updated_at: datetime
    guests: list[GuestDetailSerializer] = Field(default_factory=list)
    room_lines: list[RoomDetailSerializer] = Field(default_factory=list)
    pricing: PricingBlockSerializer | None = None
    payments: list[PaymentTxnSerializer] = Field(default_factory=list)
    attributes: dict[str, Any] | None = None
