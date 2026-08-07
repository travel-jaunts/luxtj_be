from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class HotelBase(DeclarativeBase):
    pass


class ApiCityMapRow(HotelBase):
    __tablename__ = "api_city_map"
    __table_args__ = (
        UniqueConstraint("api_fk", "api_city_code", name="uq_api_city_map_api_city_code"),
        Index("ix_api_city_map_api_fk_city_fk", "api_fk", "city_fk"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    api_fk: Mapped[str] = mapped_column(
        String(36), ForeignKey("booking_apis.id", ondelete="CASCADE"), nullable=False
    )
    city_fk: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="SET NULL"), nullable=True
    )
    api_city_code: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelMarkupRuleRow(HotelBase):
    __tablename__ = "hotel_markup_rules"
    __table_args__ = (Index("ix_hotel_markup_rules_status", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive")
    supplier_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    hotel_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    star_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    check_in_date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    check_in_date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    is_percentage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelSearchRow(HotelBase):
    __tablename__ = "hotel_searches"
    __table_args__ = (
        Index(
            "ix_hotel_searches_city_checkin_checkout",
            "city_id",
            "checkin_date",
            "checkout_date",
        ),
        Index("ix_hotel_searches_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    city_id: Mapped[str] = mapped_column(String(36), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    checkout_date: Mapped[date] = mapped_column(Date, nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(2), nullable=True)
    search_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelBookingDetailsRow(HotelBase):
    __tablename__ = "hotel_booking_details"
    __table_args__ = (
        Index("ix_hotel_booking_details_booking_source", "booking_source"),
        Index("ix_hotel_booking_details_status", "status"),
        Index("ix_hotel_booking_details_created_by_id", "created_by_id"),
        Index("ix_hotel_booking_details_hotel_crs_hotel_code", "hotel_crs_hotel_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Soft ref → CRS DB hotel_crs_hotels.code (no cross-DB FK)
    hotel_crs_hotel_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    booking_source: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="BOOKING_PENDING")
    hotel_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    star_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hotel_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hotel_check_in: Mapped[date] = mapped_column(Date, nullable=False)
    hotel_check_out: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    check_out_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rooms: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    total_adults: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_children: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    hotel_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    hotel_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    hotel_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HotelBookingTransactionDetailsRow(HotelBase):
    __tablename__ = "hotel_booking_transaction_details"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    base_fare: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    admin_markup: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    admin_markup_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    agent_markup: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    agent_markup_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    payment_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    convenience_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    convenience_value_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    convenience_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    promo_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    admin_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    admin_discount_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    admin_discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelBookingItineraryDetailsRow(HotelBase):
    __tablename__ = "hotel_booking_itinerary_details"
    __table_args__ = (
        Index("ix_hotel_booking_itinerary_details_app_reference", "app_reference"),
        Index(
            "ix_hotel_booking_itinerary_details_hotel_crs_room_code",
            "hotel_crs_room_code",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    # Soft ref → CRS DB hotel_crs_room_groups.supplier_room_code
    hotel_crs_room_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    room_type_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bed_type_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    smoking_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="BOOKING_PENDING")
    base_fare: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    adults: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    children: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelBookingCancellationPolicyRow(HotelBase):
    __tablename__ = "hotel_booking_cancellation_policies"
    __table_args__ = (
        Index("ix_hotel_booking_cancellation_policies_app_reference", "app_reference"),
        Index(
            "ix_hotel_booking_cancellation_policies_app_itinerary",
            "app_reference",
            "hotel_booking_itinerary_detail_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    hotel_booking_itinerary_detail_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("hotel_booking_itinerary_details.id", ondelete="CASCADE"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    period_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    penalty_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    penalty_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelBookingExtraFeeRow(HotelBase):
    __tablename__ = "hotel_booking_extra_fees"
    __table_args__ = (
        Index("ix_hotel_booking_extra_fees_app_reference", "app_reference"),
        Index(
            "ix_hotel_booking_extra_fees_app_itinerary",
            "app_reference",
            "hotel_booking_itinerary_detail_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    hotel_booking_itinerary_detail_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("hotel_booking_itinerary_details.id", ondelete="CASCADE"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    fee_name: Mapped[str] = mapped_column(String(191), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelBookingPaxDetailsRow(HotelBase):
    __tablename__ = "hotel_booking_pax_details"
    __table_args__ = (Index("ix_hotel_booking_pax_details_app_reference", "app_reference"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str | None] = mapped_column(String(10), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pax_type: Mapped[str] = mapped_column(String(20), nullable=False, default="Adult")
    age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelBookingCancellationQueueRow(HotelBase):
    __tablename__ = "hotel_booking_cancellation_queue"
    __table_args__ = (Index("ix_hotel_booking_cancellation_queue_app_reference", "app_reference"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    app_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    remark: Mapped[str] = mapped_column(Text, nullable=False)
    request_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    admin_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    admin_update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
