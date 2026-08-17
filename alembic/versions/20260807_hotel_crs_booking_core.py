"""add hotel crs booking geo payment currency tables

Revision ID: 20260807_hotel_crs_booking_core
Revises: 20260807_integration_registry
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_hotel_crs_booking_core"
down_revision: str | None = "20260807_integration_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Geo / currency ---
    op.create_table(
        "countries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("currency_name", sa.String(length=100), nullable=False),
        sa.Column("currency_symbol", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "cities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("country_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_cities_country_id", "cities", ["country_id"])
    op.create_index("ix_cities_country_id_name", "cities", ["country_id", "name"])
    op.create_index("ix_cities_status", "cities", ["status"])

    op.create_table(
        "active_currencies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("currency_code"),
    )

    # --- CRS ---
    op.create_table(
        "hotel_crs_suppliers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("booking_source_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_type", sa.String(length=20), nullable=False, server_default="API"),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["booking_source_id"], ["booking_apis.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "booking_source_id",
            "supplier_type",
            name="uq_hotel_crs_suppliers_booking_source_type",
        ),
    )

    op.create_table(
        "hotel_crs_hotels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_normalized", sa.String(length=255), nullable=False),
        sa.Column("star_rating", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("unique_key", sa.String(length=32), nullable=False),
        sa.Column("city_id", sa.String(length=36), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("check_in_time", sa.String(length=20), nullable=True),
        sa.Column("check_out_time", sa.String(length=20), nullable=True),
        sa.Column("front_desk_time_start", sa.String(length=20), nullable=True),
        sa.Column("front_desk_time_end", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_text", sa.Text(), nullable=True),
        sa.Column("hotel_policies", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("image", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("unique_key"),
    )
    op.create_index("ix_hotel_crs_hotels_name_normalized", "hotel_crs_hotels", ["name_normalized"])
    op.create_index("ix_hotel_crs_hotels_city_id", "hotel_crs_hotels", ["city_id"])
    op.create_index(
        "ix_hotel_crs_hotels_city_id_star_rating",
        "hotel_crs_hotels",
        ["city_id", "star_rating"],
    )
    op.create_index(
        "ix_hotel_crs_hotels_city_id_status",
        "hotel_crs_hotels",
        ["city_id", "status"],
    )

    op.create_table(
        "hotel_crs_amenities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("image_file_id", sa.String(length=36), nullable=True),
        sa.Column("scope", sa.String(length=20), nullable=False, server_default="both"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_hotel_crs_amenities_name", "hotel_crs_amenities", ["name"])
    op.create_index("ix_hotel_crs_amenities_category", "hotel_crs_amenities", ["category"])
    op.create_index(
        "ix_hotel_crs_amenities_image_file_id",
        "hotel_crs_amenities",
        ["image_file_id"],
    )

    op.create_table(
        "hotel_crs_supplier_hotel_map",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_hotel_code", sa.String(length=100), nullable=False),
        sa.Column("hotel_id", sa.String(length=36), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["hotel_crs_suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "supplier_id",
            "supplier_hotel_code",
            "hotel_id",
            name="uq_hotel_crs_supplier_hotel_map",
        ),
    )
    op.create_index(
        "ix_hotel_crs_supplier_hotel_map_supplier_code",
        "hotel_crs_supplier_hotel_map",
        ["supplier_id", "supplier_hotel_code"],
    )

    op.create_table(
        "hotel_crs_hotel_images",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hotel_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column("category_slug", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_hotel_crs_hotel_images_hotel_id", "hotel_crs_hotel_images", ["hotel_id"])

    op.create_table(
        "hotel_crs_hotel_amenity_map",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hotel_id", sa.String(length=36), nullable=False),
        sa.Column("amenity_id", sa.String(length=36), nullable=False),
        sa.Column("group_name", sa.String(length=100), nullable=True),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["amenity_id"], ["hotel_crs_amenities.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "hotel_id",
            "amenity_id",
            "group_name",
            name="uq_hotel_crs_hotel_amenity_map",
        ),
    )
    op.create_index(
        "ix_hotel_crs_hotel_amenity_map_hotel_id",
        "hotel_crs_hotel_amenity_map",
        ["hotel_id"],
    )
    op.create_index(
        "ix_hotel_crs_hotel_amenity_map_amenity_id",
        "hotel_crs_hotel_amenity_map",
        ["amenity_id"],
    )

    op.create_table(
        "hotel_crs_room_groups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hotel_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_room_code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("main_name", sa.String(length=255), nullable=True),
        sa.Column("bedding_type", sa.String(length=100), nullable=True),
        sa.Column("bathroom_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Numeric(10, 2), nullable=True),
        sa.Column("capacity", sa.SmallInteger(), nullable=True),
        sa.Column("rg_ext", sa.JSON(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "hotel_id",
            "supplier_room_code",
            name="uq_hotel_crs_room_groups_hotel_supplier_code",
        ),
    )
    op.create_index("ix_hotel_crs_room_groups_hotel_id", "hotel_crs_room_groups", ["hotel_id"])
    op.create_index(
        "ix_hotel_crs_room_groups_hotel_id_name",
        "hotel_crs_room_groups",
        ["hotel_id", "name"],
    )

    op.create_table(
        "hotel_crs_room_images",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("room_group_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("category_slug", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["room_group_id"], ["hotel_crs_room_groups.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_hotel_crs_room_images_room_group_id",
        "hotel_crs_room_images",
        ["room_group_id"],
    )

    op.create_table(
        "hotel_crs_room_amenity_map",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("room_group_id", sa.String(length=36), nullable=False),
        sa.Column("amenity_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["room_group_id"], ["hotel_crs_room_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["amenity_id"], ["hotel_crs_amenities.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "room_group_id",
            "amenity_id",
            name="uq_hotel_crs_room_amenity_map",
        ),
    )
    op.create_index(
        "ix_hotel_crs_room_amenity_map_amenity_id",
        "hotel_crs_room_amenity_map",
        ["amenity_id"],
    )

    # --- Helpers ---
    op.create_table(
        "api_city_map",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("api_fk", sa.String(length=36), nullable=False),
        sa.Column("city_fk", sa.String(length=36), nullable=True),
        sa.Column("api_city_code", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_fk"], ["booking_apis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_fk"], ["cities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("api_fk", "api_city_code", name="uq_api_city_map_api_city_code"),
    )
    op.create_index("ix_api_city_map_api_fk_city_fk", "api_city_map", ["api_fk", "city_fk"])

    op.create_table(
        "hotel_markup_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="inactive"),
        sa.Column("supplier_code", sa.String(length=50), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("city_id", sa.String(length=36), nullable=True),
        sa.Column("hotel_code", sa.String(length=100), nullable=True),
        sa.Column("star_rating", sa.SmallInteger(), nullable=True),
        sa.Column("check_in_date_from", sa.Date(), nullable=True),
        sa.Column("check_in_date_to", sa.Date(), nullable=True),
        sa.Column("markup_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("is_percentage", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hotel_markup_rules_status", "hotel_markup_rules", ["status"])

    # --- Search + booking ---
    op.create_table(
        "hotel_searches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("city_id", sa.String(length=36), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("checkout_date", sa.Date(), nullable=False),
        sa.Column("nationality", sa.String(length=2), nullable=True),
        sa.Column("search_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_hotel_searches_city_checkin_checkout",
        "hotel_searches",
        ["city_id", "checkin_date", "checkout_date"],
    )
    op.create_index("ix_hotel_searches_created_at", "hotel_searches", ["created_at"])

    op.create_table(
        "hotel_booking_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hotel_crs_hotel_id", sa.String(length=36), nullable=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("booking_source", sa.String(length=50), nullable=False),
        sa.Column("booking_reference", sa.String(length=100), nullable=True),
        sa.Column("confirmation_reference", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="BOOKING_PENDING",
        ),
        sa.Column("hotel_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("star_rating", sa.SmallInteger(), nullable=True),
        sa.Column("hotel_code", sa.String(length=100), nullable=True),
        sa.Column("hotel_check_in", sa.Date(), nullable=False),
        sa.Column("hotel_check_out", sa.Date(), nullable=False),
        sa.Column("check_in_time", sa.String(length=20), nullable=True),
        sa.Column("check_out_time", sa.String(length=20), nullable=True),
        sa.Column("rooms", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("total_adults", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("total_children", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("hotel_image", sa.Text(), nullable=True),
        sa.Column("hotel_address", sa.Text(), nullable=True),
        sa.Column("hotel_location", sa.String(length=255), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["hotel_crs_hotel_id"], ["hotel_crs_hotels.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("app_reference"),
    )
    op.create_index(
        "ix_hotel_booking_details_booking_source",
        "hotel_booking_details",
        ["booking_source"],
    )
    op.create_index("ix_hotel_booking_details_status", "hotel_booking_details", ["status"])
    op.create_index(
        "ix_hotel_booking_details_created_by_id",
        "hotel_booking_details",
        ["created_by_id"],
    )
    op.create_index(
        "ix_hotel_booking_details_hotel_crs_hotel_id",
        "hotel_booking_details",
        ["hotel_crs_hotel_id"],
    )

    op.create_table(
        "hotel_booking_transaction_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("base_fare", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("taxes", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("admin_markup", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("admin_markup_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("agent_markup", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("agent_markup_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payment_mode", sa.String(length=30), nullable=True),
        sa.Column("convenience_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("convenience_value_type", sa.String(length=20), nullable=True),
        sa.Column("convenience_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("promo_code", sa.String(length=100), nullable=True),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("admin_discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("admin_discount_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("admin_discount_type", sa.String(length=20), nullable=True),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("conversion_rate", sa.Numeric(18, 8), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("app_reference"),
    )

    op.create_table(
        "hotel_booking_itinerary_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("room_type_name", sa.String(length=255), nullable=True),
        sa.Column("bed_type_code", sa.String(length=100), nullable=True),
        sa.Column("smoking_preference", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="BOOKING_PENDING",
        ),
        sa.Column("base_fare", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("taxes", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("adults", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("children", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_hotel_booking_itinerary_details_app_reference",
        "hotel_booking_itinerary_details",
        ["app_reference"],
    )

    op.create_table(
        "hotel_booking_cancellation_policies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("hotel_booking_itinerary_detail_id", sa.String(length=36), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("period_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("penalty_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("penalty_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hotel_booking_itinerary_detail_id"],
            ["hotel_booking_itinerary_details.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_hotel_booking_cancellation_policies_app_reference",
        "hotel_booking_cancellation_policies",
        ["app_reference"],
    )
    op.create_index(
        "ix_hotel_booking_cancellation_policies_app_itinerary",
        "hotel_booking_cancellation_policies",
        ["app_reference", "hotel_booking_itinerary_detail_id"],
    )

    op.create_table(
        "hotel_booking_extra_fees",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("hotel_booking_itinerary_detail_id", sa.String(length=36), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("fee_name", sa.String(length=191), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_included", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hotel_booking_itinerary_detail_id"],
            ["hotel_booking_itinerary_details.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_hotel_booking_extra_fees_app_reference",
        "hotel_booking_extra_fees",
        ["app_reference"],
    )
    op.create_index(
        "ix_hotel_booking_extra_fees_app_itinerary",
        "hotel_booking_extra_fees",
        ["app_reference", "hotel_booking_itinerary_detail_id"],
    )

    op.create_table(
        "hotel_booking_pax_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=10), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("phone_code", sa.String(length=10), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("pax_type", sa.String(length=20), nullable=False, server_default="Adult"),
        sa.Column("age", sa.SmallInteger(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_hotel_booking_pax_details_app_reference",
        "hotel_booking_pax_details",
        ["app_reference"],
    )

    op.create_table(
        "hotel_booking_cancellation_queue",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("remark", sa.Text(), nullable=False),
        sa.Column("request_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_remark", sa.Text(), nullable=True),
        sa.Column(
            "request_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("admin_update_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_hotel_booking_cancellation_queue_app_reference",
        "hotel_booking_cancellation_queue",
        ["app_reference"],
    )

    # --- Payment / audit ---
    op.create_table(
        "payment_gateway_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("flight_booking_details_id", sa.String(length=36), nullable=True),
        sa.Column("pg_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("booking_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("request_params", sa.JSON(), nullable=True),
        sa.Column("response_params", sa.JSON(), nullable=True),
        sa.Column("pg_reference_id", sa.String(length=255), nullable=True),
        sa.Column("pg_currency", sa.String(length=3), nullable=True),
        sa.Column("pg_currency_conversion_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("pg_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index(
        "ix_payment_gateway_transactions_app_reference",
        "payment_gateway_transactions",
        ["app_reference"],
    )
    op.create_index(
        "ix_payment_gateway_transactions_pg_code",
        "payment_gateway_transactions",
        ["pg_code"],
    )
    op.create_index(
        "ix_payment_gateway_transactions_flight_booking_details_id",
        "payment_gateway_transactions",
        ["flight_booking_details_id"],
    )

    op.create_table(
        "booking_api_request_responses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("booking_api_id", sa.String(length=36), nullable=False),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("request_format", sa.String(length=20), nullable=False),
        sa.Column("request_url", sa.String(length=2048), nullable=False),
        sa.Column("request_headers", sa.Text(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("response_status_code", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["booking_api_id"], ["booking_apis.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_booking_api_request_responses_booking_api_id",
        "booking_api_request_responses",
        ["booking_api_id"],
    )
    op.create_index(
        "ix_booking_api_request_responses_request_type",
        "booking_api_request_responses",
        ["request_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_booking_api_request_responses_request_type",
        table_name="booking_api_request_responses",
    )
    op.drop_index(
        "ix_booking_api_request_responses_booking_api_id",
        table_name="booking_api_request_responses",
    )
    op.drop_table("booking_api_request_responses")

    op.drop_index(
        "ix_payment_gateway_transactions_flight_booking_details_id",
        table_name="payment_gateway_transactions",
    )
    op.drop_index(
        "ix_payment_gateway_transactions_pg_code",
        table_name="payment_gateway_transactions",
    )
    op.drop_index(
        "ix_payment_gateway_transactions_app_reference",
        table_name="payment_gateway_transactions",
    )
    op.drop_table("payment_gateway_transactions")

    op.drop_index(
        "ix_hotel_booking_cancellation_queue_app_reference",
        table_name="hotel_booking_cancellation_queue",
    )
    op.drop_table("hotel_booking_cancellation_queue")

    op.drop_index(
        "ix_hotel_booking_pax_details_app_reference",
        table_name="hotel_booking_pax_details",
    )
    op.drop_table("hotel_booking_pax_details")

    op.drop_index(
        "ix_hotel_booking_extra_fees_app_itinerary",
        table_name="hotel_booking_extra_fees",
    )
    op.drop_index(
        "ix_hotel_booking_extra_fees_app_reference",
        table_name="hotel_booking_extra_fees",
    )
    op.drop_table("hotel_booking_extra_fees")

    op.drop_index(
        "ix_hotel_booking_cancellation_policies_app_itinerary",
        table_name="hotel_booking_cancellation_policies",
    )
    op.drop_index(
        "ix_hotel_booking_cancellation_policies_app_reference",
        table_name="hotel_booking_cancellation_policies",
    )
    op.drop_table("hotel_booking_cancellation_policies")

    op.drop_index(
        "ix_hotel_booking_itinerary_details_app_reference",
        table_name="hotel_booking_itinerary_details",
    )
    op.drop_table("hotel_booking_itinerary_details")
    op.drop_table("hotel_booking_transaction_details")

    op.drop_index(
        "ix_hotel_booking_details_hotel_crs_hotel_id",
        table_name="hotel_booking_details",
    )
    op.drop_index("ix_hotel_booking_details_created_by_id", table_name="hotel_booking_details")
    op.drop_index("ix_hotel_booking_details_status", table_name="hotel_booking_details")
    op.drop_index("ix_hotel_booking_details_booking_source", table_name="hotel_booking_details")
    op.drop_table("hotel_booking_details")

    op.drop_index("ix_hotel_searches_created_at", table_name="hotel_searches")
    op.drop_index("ix_hotel_searches_city_checkin_checkout", table_name="hotel_searches")
    op.drop_table("hotel_searches")

    op.drop_index("ix_hotel_markup_rules_status", table_name="hotel_markup_rules")
    op.drop_table("hotel_markup_rules")

    op.drop_index("ix_api_city_map_api_fk_city_fk", table_name="api_city_map")
    op.drop_table("api_city_map")

    op.drop_index(
        "ix_hotel_crs_room_amenity_map_amenity_id",
        table_name="hotel_crs_room_amenity_map",
    )
    op.drop_table("hotel_crs_room_amenity_map")

    op.drop_index("ix_hotel_crs_room_images_room_group_id", table_name="hotel_crs_room_images")
    op.drop_table("hotel_crs_room_images")

    op.drop_index("ix_hotel_crs_room_groups_hotel_id_name", table_name="hotel_crs_room_groups")
    op.drop_index("ix_hotel_crs_room_groups_hotel_id", table_name="hotel_crs_room_groups")
    op.drop_table("hotel_crs_room_groups")

    op.drop_index(
        "ix_hotel_crs_hotel_amenity_map_amenity_id",
        table_name="hotel_crs_hotel_amenity_map",
    )
    op.drop_index(
        "ix_hotel_crs_hotel_amenity_map_hotel_id",
        table_name="hotel_crs_hotel_amenity_map",
    )
    op.drop_table("hotel_crs_hotel_amenity_map")

    op.drop_index("ix_hotel_crs_hotel_images_hotel_id", table_name="hotel_crs_hotel_images")
    op.drop_table("hotel_crs_hotel_images")

    op.drop_index(
        "ix_hotel_crs_supplier_hotel_map_supplier_code",
        table_name="hotel_crs_supplier_hotel_map",
    )
    op.drop_table("hotel_crs_supplier_hotel_map")

    op.drop_index("ix_hotel_crs_amenities_image_file_id", table_name="hotel_crs_amenities")
    op.drop_index("ix_hotel_crs_amenities_category", table_name="hotel_crs_amenities")
    op.drop_index("ix_hotel_crs_amenities_name", table_name="hotel_crs_amenities")
    op.drop_table("hotel_crs_amenities")

    op.drop_index("ix_hotel_crs_hotels_city_id_status", table_name="hotel_crs_hotels")
    op.drop_index("ix_hotel_crs_hotels_city_id_star_rating", table_name="hotel_crs_hotels")
    op.drop_index("ix_hotel_crs_hotels_city_id", table_name="hotel_crs_hotels")
    op.drop_index("ix_hotel_crs_hotels_name_normalized", table_name="hotel_crs_hotels")
    op.drop_table("hotel_crs_hotels")
    op.drop_table("hotel_crs_suppliers")

    op.drop_table("active_currencies")
    op.drop_index("ix_cities_status", table_name="cities")
    op.drop_index("ix_cities_country_id_name", table_name="cities")
    op.drop_index("ix_cities_country_id", table_name="cities")
    op.drop_table("cities")
    op.drop_table("countries")
