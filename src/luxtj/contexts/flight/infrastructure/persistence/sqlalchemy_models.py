"""Flight persistence models — search session + booking core tables."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class FlightBase(DeclarativeBase):
    pass


class FlightSearchRow(FlightBase):
    """B2C flight search session (PreSearch → Search)."""

    __tablename__ = "flight_searches"
    __table_args__ = (Index("ix_flight_searches_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trip_type: Mapped[str] = mapped_column(String(20), nullable=False, default="oneway")
    cabin_class: Mapped[str] = mapped_column(String(30), nullable=False, default="Economy")
    adult_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    child_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    infant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    search_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FlightBookingDetailsRow(FlightBase):
    """Master flight booking row (draft from PreBook onward)."""

    __tablename__ = "flight_booking_details"
    __table_args__ = (
        Index("ix_flight_booking_details_booking_source", "booking_source"),
        Index("ix_flight_booking_details_status", "status"),
        Index("ix_flight_booking_details_created_by_id", "created_by_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    booking_source: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    book_guid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gdspnr: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="BOOKING_STARTED")
    trip_type: Mapped[str] = mapped_column(String(20), nullable=False, default="oneway")
    cabin_class: Mapped[str | None] = mapped_column(String(30), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(10), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(10), nullable=True)
    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    details_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FlightBookingTransactionDetailsRow(FlightBase):
    """Money ledger for a flight booking (admin currency amounts)."""

    __tablename__ = "flight_booking_transaction_details"
    __table_args__ = (
        Index("ix_flight_booking_txn_app_reference", "app_reference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("flight_booking_details.app_reference", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    basic_fare: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    airline_tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    admin_markup: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    admin_discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    promocode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    convenience_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_fare: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    # B2C display currency at book time (amounts above are admin).
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    currency_conversion_rate: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False, default=1
    )
    payment_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pax_wise_fare_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FlightBookingItineraryDetailsRow(FlightBase):
    """Segment / offer snapshot rows for a booking."""

    __tablename__ = "flight_booking_itinerary_details"
    __table_args__ = (Index("ix_flight_itinerary_app_reference", "app_reference"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("flight_booking_details.app_reference", ondelete="CASCADE"),
        nullable=False,
    )
    rph: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    airline_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(10), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(10), nullable=True)
    departure_datetime: Mapped[str | None] = mapped_column(String(40), nullable=True)
    arrival_datetime: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cabin_class: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pnr: Mapped[str | None] = mapped_column(String(50), nullable=True)
    segment_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FlightBookingPassengerDetailsRow(FlightBase):
    """Passenger rows for a booking."""

    __tablename__ = "flight_booking_passenger_details"
    __table_args__ = (Index("ix_flight_pax_app_reference", "app_reference"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("flight_booking_details.app_reference", ondelete="CASCADE"),
        nullable=False,
    )
    pass_guid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age_type: Mapped[str] = mapped_column(String(20), nullable=False, default="Adult")
    title: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(3), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_expiry: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ticket_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FlightMarkupRuleRow(FlightBase):
    """Admin flight markup rules (TeenvaFlightMarkup engine)."""

    __tablename__ = "flight_markup_rules"
    __table_args__ = (Index("ix_flight_markup_rules_status", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive")
    airline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(10), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cabin_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    travel_date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    travel_date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    is_percentage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
