"""Hotel CRS + region catalogue models (separate CRS database).

Cross-database references (booking_apis, cities) are soft string ids — no FKs.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class CrsBase(DeclarativeBase):
    pass


class NewCitiesNRegionRow(CrsBase):
    __tablename__ = "new_cities_n_regions"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_new_cities_n_regions_dedupe_key"),
        Index("ix_new_cities_n_regions_country_code", "country_code"),
        Index("ix_new_cities_n_regions_name", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="Unknown")
    iata: Mapped[str | None] = mapped_column(String(3), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    country_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BookingSourceRegionMapRow(CrsBase):
    __tablename__ = "booking_source_region_map"
    __table_args__ = (
        UniqueConstraint(
            "booking_source_id",
            "booking_source_region_code",
            name="uq_booking_source_region_map_code",
        ),
        UniqueConstraint(
            "booking_source_id",
            "new_cities_n_region_id",
            name="uq_booking_source_region_map_region",
        ),
        Index("ix_booking_source_region_map_source", "booking_source_id"),
        Index("ix_booking_source_region_map_region", "new_cities_n_region_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Soft ref → main DB booking_apis.id
    booking_source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    new_cities_n_region_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("new_cities_n_regions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    booking_source_region_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegionMappingRunRow(CrsBase):
    __tablename__ = "region_mapping_runs"
    __table_args__ = (
        Index("ix_region_mapping_runs_source_status", "booking_source_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    booking_source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="admin", server_default="admin"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending"
    )
    dump_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    zst_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    matched_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cities_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelMappingRunRow(CrsBase):
    __tablename__ = "hotel_mapping_runs"
    __table_args__ = (
        Index("ix_hotel_mapping_runs_source_status", "booking_source_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    booking_source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parent_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("hotel_mapping_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    dump_type: Mapped[str] = mapped_column(String(30), nullable=False, default="full")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    dump_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    zst_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StagingHotelRow(CrsBase):
    __tablename__ = "staging_hotels"
    __table_args__ = (
        Index(
            "ix_staging_hotels_run_promote",
            "mapping_run_id",
            "hotel_promoted_at",
            "promote_claimed_at",
        ),
        Index("ix_staging_hotels_run_code", "mapping_run_id", "supplier_hotel_code"),
        Index(
            "ix_staging_hotels_run_rooms_claim",
            "mapping_run_id",
            "hotel_promoted_at",
            "rooms_promoted_at",
            "extras_claimed_at",
        ),
        Index("ix_staging_hotels_dedupe_key", "dedupe_key"),
        Index("ix_staging_hotels_region_id", "region_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mapping_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_mapping_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    shard_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supplier_hotel_code: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(32), nullable=False)
    region_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("new_cities_n_regions.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    star_rating: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    amenity_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    image_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    room_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    policy_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    accommodation_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hotel_chain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    check_in_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    check_in_time_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    check_out_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    front_desk_time_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    front_desk_time_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hotel_promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rooms_promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    promote_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extras_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StagingRoomRow(CrsBase):
    __tablename__ = "staging_rooms"
    __table_args__ = (
        UniqueConstraint(
            "mapping_run_id",
            "supplier_hotel_code",
            "room_group_id",
            name="uq_staging_rooms_run_hotel_room",
        ),
        Index("ix_staging_rooms_run_hotel", "mapping_run_id", "supplier_hotel_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mapping_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_mapping_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    shard_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supplier_hotel_code: Mapped[str] = mapped_column(String(64), nullable=False)
    room_group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    main_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amenity_slugs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    image_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rg_ext: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    name_struct: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    images_ext: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsSupplierRow(CrsBase):
    __tablename__ = "hotel_crs_suppliers"
    __table_args__ = (
        UniqueConstraint(
            "booking_source_id",
            "supplier_type",
            name="uq_hotel_crs_suppliers_booking_source_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Soft ref → main DB booking_apis.id
    booking_source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(20), nullable=False, default="API")
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelRow(CrsBase):
    __tablename__ = "hotel_crs_hotels"
    __table_args__ = (
        Index("ix_hotel_crs_hotels_name_normalized", "name_normalized"),
        Index("ix_hotel_crs_hotels_region_id", "region_id"),
        Index("ix_hotel_crs_hotels_region_id_star_rating", "region_id", "star_rating"),
        Index("ix_hotel_crs_hotels_region_id_status", "region_id", "status"),
        Index("ix_hotel_crs_hotels_code", "code"),
        Index("ix_hotel_crs_hotels_created_at_id", "created_at", "id"),
        Index("ix_hotel_crs_hotels_status_created_at_id", "status", "created_at", "id"),
        Index("ix_hotel_crs_hotels_accommodation_type", "accommodation_type"),
        Index("ix_hotel_crs_hotels_hotel_chain", "hotel_chain"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    star_rating: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    unique_key: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    region_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("new_cities_n_regions.id", ondelete="SET NULL"),
        nullable=True,
    )
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    check_in_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    check_out_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    front_desk_time_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    front_desk_time_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    hotel_policies: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    accommodation_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    accommodation_type_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hotel_chain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    check_in_time_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    giata_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_closed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_gender_specification_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    floors_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rooms_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_built: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    electricity_frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    electricity_voltage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    electricity_sockets: Mapped[str | None] = mapped_column(String(255), nullable=True)
    star_certificate_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    star_certificate_valid_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    keys_pickup_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    keys_pickup_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    keys_pickup_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keys_pickup_is_contactless: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    keys_pickup_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    keys_pickup_extra_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    register_record: Mapped[str | None] = mapped_column(String(100), nullable=True)
    register_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    register_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    register_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    register_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    register_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    register_status_end_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    register_taxpayer_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    register_state_registration_number: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    register_work_time: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsSupplierHotelMapRow(CrsBase):
    __tablename__ = "hotel_crs_supplier_hotel_map"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "supplier_hotel_code",
            "hotel_id",
            name="uq_hotel_crs_supplier_hotel_map",
        ),
        Index(
            "ix_hotel_crs_supplier_hotel_map_supplier_code",
            "supplier_id",
            "supplier_hotel_code",
        ),
        Index("ix_hotel_crs_supplier_hotel_map_hotel_id", "hotel_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_hotel_code: Mapped[str] = mapped_column(String(100), nullable=False)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelImageRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_images"
    __table_args__ = (Index("ix_hotel_crs_hotel_images_hotel_id", "hotel_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsAmenityRow(CrsBase):
    __tablename__ = "hotel_crs_amenities"
    __table_args__ = (
        Index("ix_hotel_crs_amenities_name", "name"),
        Index("ix_hotel_crs_amenities_category", "category"),
        Index("ix_hotel_crs_amenities_image_file_id", "image_file_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="both")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelAmenityMapRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_amenity_map"
    __table_args__ = (
        UniqueConstraint(
            "hotel_id",
            "amenity_id",
            "group_name",
            name="uq_hotel_crs_hotel_amenity_map",
        ),
        Index("ix_hotel_crs_hotel_amenity_map_hotel_id", "hotel_id"),
        Index("ix_hotel_crs_hotel_amenity_map_amenity_id", "amenity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    amenity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_amenities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsRoomGroupRow(CrsBase):
    __tablename__ = "hotel_crs_room_groups"
    __table_args__ = (
        UniqueConstraint(
            "hotel_id",
            "supplier_room_code",
            name="uq_hotel_crs_room_groups_hotel_supplier_code",
        ),
        Index("ix_hotel_crs_room_groups_hotel_id", "hotel_id"),
        Index("ix_hotel_crs_room_groups_hotel_id_name", "hotel_id", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_room_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    main_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bedding_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bathroom_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    capacity: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    balcony: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    view_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    view_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    room_class: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    class_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quality: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    quality_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_family: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_club: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    floor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelDescriptionSectionRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_description_sections"
    __table_args__ = (
        Index("ix_hotel_crs_hotel_description_sections_hotel_id", "hotel_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelPaymentMethodRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_payment_methods"
    __table_args__ = (
        UniqueConstraint(
            "hotel_id", "method_code", name="uq_hotel_crs_hotel_payment_methods"
        ),
        Index("ix_hotel_crs_hotel_payment_methods_hotel_id", "hotel_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    method_code: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelFeatureTagRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_feature_tags"
    __table_args__ = (
        UniqueConstraint("hotel_id", "tag", name="uq_hotel_crs_hotel_feature_tags"),
        Index("ix_hotel_crs_hotel_feature_tags_hotel_id", "hotel_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelPolicySectionRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_policy_sections"
    __table_args__ = (Index("ix_hotel_crs_hotel_policy_sections_hotel_id", "hotel_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelPolicyItemRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_policy_items"
    __table_args__ = (
        Index("ix_hotel_crs_hotel_policy_items_hotel_id", "hotel_id"),
        Index("ix_hotel_crs_hotel_policy_items_hotel_category", "hotel_id", "category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelPolicyItemAttrRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_policy_item_attrs"
    __table_args__ = (
        UniqueConstraint(
            "policy_item_id",
            "attr_key",
            name="uq_hotel_crs_hotel_policy_item_attrs",
        ),
        Index("ix_hotel_crs_hotel_policy_item_attrs_item_id", "policy_item_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    policy_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotel_policy_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    attr_key: Mapped[str] = mapped_column(String(80), nullable=False)
    attr_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsHotelRegisterRoomCategoryRow(CrsBase):
    __tablename__ = "hotel_crs_hotel_register_room_categories"
    __table_args__ = (
        Index("ix_hotel_crs_hotel_register_room_categories_hotel_id", "hotel_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_hotels.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rooms_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsRoomImageRow(CrsBase):
    __tablename__ = "hotel_crs_room_images"
    __table_args__ = (Index("ix_hotel_crs_room_images_room_group_id", "room_group_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_room_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    category_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HotelCrsRoomAmenityMapRow(CrsBase):
    __tablename__ = "hotel_crs_room_amenity_map"
    __table_args__ = (
        UniqueConstraint(
            "room_group_id",
            "amenity_id",
            name="uq_hotel_crs_room_amenity_map",
        ),
        Index("ix_hotel_crs_room_amenity_map_amenity_id", "amenity_id"),
        Index("ix_hotel_crs_room_amenity_map_room_group_id", "room_group_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_room_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    amenity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hotel_crs_amenities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
