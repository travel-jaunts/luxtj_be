"""RateHawk full content columns on CRS hotels/rooms + staging.

Revision ID: 20260807_crs_ratehawk_content
Revises: 20260807_crs_inventory_indexes
Create Date: 2026-08-07

Adds nullable columns so RateHawk (and future suppliers) can omit fields
without breaking inserts.

Idempotent: safe when ``crs_initial`` already created the current ORM schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
)
from sqlalchemy.dialects import postgresql

revision: str = "20260807_crs_ratehawk_content"
down_revision: str | None = "20260807_crs_inventory_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- hotel_crs_hotels ---
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("accommodation_type", sa.String(length=100), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("accommodation_type_code", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("hotel_chain", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("check_in_time_end", sa.String(length=20), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("giata_code", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("is_closed", sa.Boolean(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("is_gender_specification_required", sa.Boolean(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("description_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("star_certificate", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("payment_methods", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("serp_filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("supplier_slug", sa.String(length=255), nullable=True),
    )
    create_index_if_missing(
        "ix_hotel_crs_hotels_accommodation_type",
        "hotel_crs_hotels",
        ["accommodation_type"],
    )
    create_index_if_missing(
        "ix_hotel_crs_hotels_hotel_chain",
        "hotel_crs_hotels",
        ["hotel_chain"],
    )

    # --- hotel_crs_room_groups ---
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("description", sa.Text(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("name_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("bedrooms", sa.SmallInteger(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("balcony", sa.Boolean(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("view_code", sa.SmallInteger(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("room_class", sa.SmallInteger(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("quality", sa.SmallInteger(), nullable=True),
    )

    # --- staging_hotels ---
    add_column_if_missing(
        "staging_hotels",
        sa.Column("accommodation_type", sa.String(length=100), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("hotel_chain", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("check_in_time", sa.String(length=20), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("check_in_time_end", sa.String(length=20), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("check_out_time", sa.String(length=20), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("front_desk_time_start", sa.String(length=20), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("front_desk_time_end", sa.String(length=20), nullable=True),
    )
    add_column_if_missing(
        "staging_hotels",
        sa.Column("content_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # --- staging_rooms ---
    add_column_if_missing(
        "staging_rooms",
        sa.Column("main_name", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "staging_rooms",
        sa.Column("rg_ext", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "staging_rooms",
        sa.Column("name_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "staging_rooms",
        sa.Column("images_ext", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    drop_column_if_exists("staging_rooms", "images_ext")
    drop_column_if_exists("staging_rooms", "name_struct")
    drop_column_if_exists("staging_rooms", "rg_ext")
    drop_column_if_exists("staging_rooms", "main_name")

    drop_column_if_exists("staging_hotels", "content_payload")
    drop_column_if_exists("staging_hotels", "front_desk_time_end")
    drop_column_if_exists("staging_hotels", "front_desk_time_start")
    drop_column_if_exists("staging_hotels", "check_out_time")
    drop_column_if_exists("staging_hotels", "check_in_time_end")
    drop_column_if_exists("staging_hotels", "check_in_time")
    drop_column_if_exists("staging_hotels", "hotel_chain")
    drop_column_if_exists("staging_hotels", "accommodation_type")

    drop_column_if_exists("hotel_crs_room_groups", "quality")
    drop_column_if_exists("hotel_crs_room_groups", "room_class")
    drop_column_if_exists("hotel_crs_room_groups", "view_code")
    drop_column_if_exists("hotel_crs_room_groups", "balcony")
    drop_column_if_exists("hotel_crs_room_groups", "bedrooms")
    drop_column_if_exists("hotel_crs_room_groups", "name_struct")
    drop_column_if_exists("hotel_crs_room_groups", "description")

    drop_index_if_exists("ix_hotel_crs_hotels_hotel_chain", "hotel_crs_hotels")
    drop_index_if_exists("ix_hotel_crs_hotels_accommodation_type", "hotel_crs_hotels")
    drop_column_if_exists("hotel_crs_hotels", "supplier_slug")
    drop_column_if_exists("hotel_crs_hotels", "serp_filters")
    drop_column_if_exists("hotel_crs_hotels", "payment_methods")
    drop_column_if_exists("hotel_crs_hotels", "star_certificate")
    drop_column_if_exists("hotel_crs_hotels", "keys_pickup")
    drop_column_if_exists("hotel_crs_hotels", "facts")
    drop_column_if_exists("hotel_crs_hotels", "description_struct")
    drop_column_if_exists("hotel_crs_hotels", "is_gender_specification_required")
    drop_column_if_exists("hotel_crs_hotels", "is_closed")
    drop_column_if_exists("hotel_crs_hotels", "giata_code")
    drop_column_if_exists("hotel_crs_hotels", "check_in_time_end")
    drop_column_if_exists("hotel_crs_hotels", "hotel_chain")
    drop_column_if_exists("hotel_crs_hotels", "accommodation_type_code")
    drop_column_if_exists("hotel_crs_hotels", "accommodation_type")
