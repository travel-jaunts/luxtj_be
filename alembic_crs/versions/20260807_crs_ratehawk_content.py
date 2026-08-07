"""RateHawk full content columns on CRS hotels/rooms + staging.

Revision ID: 20260807_crs_ratehawk_content
Revises: 20260807_crs_inventory_indexes
Create Date: 2026-08-07

Adds nullable columns so RateHawk (and future suppliers) can omit fields
without breaking inserts.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260807_crs_ratehawk_content"
down_revision: str | None = "20260807_crs_inventory_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- hotel_crs_hotels ---
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("accommodation_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("accommodation_type_code", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("hotel_chain", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("check_in_time_end", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("giata_code", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("is_closed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("is_gender_specification_required", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("description_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("keys_pickup", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("star_certificate", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("payment_methods", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("serp_filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("supplier_slug", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_hotel_crs_hotels_accommodation_type",
        "hotel_crs_hotels",
        ["accommodation_type"],
    )
    op.create_index(
        "ix_hotel_crs_hotels_hotel_chain",
        "hotel_crs_hotels",
        ["hotel_chain"],
    )

    # --- hotel_crs_room_groups ---
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("name_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("bedrooms", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("balcony", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("view_code", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("room_class", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "hotel_crs_room_groups",
        sa.Column("quality", sa.SmallInteger(), nullable=True),
    )

    # --- staging_hotels ---
    op.add_column(
        "staging_hotels",
        sa.Column("accommodation_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("hotel_chain", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("check_in_time", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("check_in_time_end", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("check_out_time", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("front_desk_time_start", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("front_desk_time_end", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "staging_hotels",
        sa.Column("content_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # --- staging_rooms ---
    op.add_column(
        "staging_rooms",
        sa.Column("main_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "staging_rooms",
        sa.Column("rg_ext", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "staging_rooms",
        sa.Column("name_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "staging_rooms",
        sa.Column("images_ext", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("staging_rooms", "images_ext")
    op.drop_column("staging_rooms", "name_struct")
    op.drop_column("staging_rooms", "rg_ext")
    op.drop_column("staging_rooms", "main_name")

    op.drop_column("staging_hotels", "content_payload")
    op.drop_column("staging_hotels", "front_desk_time_end")
    op.drop_column("staging_hotels", "front_desk_time_start")
    op.drop_column("staging_hotels", "check_out_time")
    op.drop_column("staging_hotels", "check_in_time_end")
    op.drop_column("staging_hotels", "check_in_time")
    op.drop_column("staging_hotels", "hotel_chain")
    op.drop_column("staging_hotels", "accommodation_type")

    op.drop_column("hotel_crs_room_groups", "quality")
    op.drop_column("hotel_crs_room_groups", "room_class")
    op.drop_column("hotel_crs_room_groups", "view_code")
    op.drop_column("hotel_crs_room_groups", "balcony")
    op.drop_column("hotel_crs_room_groups", "bedrooms")
    op.drop_column("hotel_crs_room_groups", "name_struct")
    op.drop_column("hotel_crs_room_groups", "description")

    op.drop_index("ix_hotel_crs_hotels_hotel_chain", table_name="hotel_crs_hotels")
    op.drop_index("ix_hotel_crs_hotels_accommodation_type", table_name="hotel_crs_hotels")
    op.drop_column("hotel_crs_hotels", "supplier_slug")
    op.drop_column("hotel_crs_hotels", "serp_filters")
    op.drop_column("hotel_crs_hotels", "payment_methods")
    op.drop_column("hotel_crs_hotels", "star_certificate")
    op.drop_column("hotel_crs_hotels", "keys_pickup")
    op.drop_column("hotel_crs_hotels", "facts")
    op.drop_column("hotel_crs_hotels", "description_struct")
    op.drop_column("hotel_crs_hotels", "is_gender_specification_required")
    op.drop_column("hotel_crs_hotels", "is_closed")
    op.drop_column("hotel_crs_hotels", "giata_code")
    op.drop_column("hotel_crs_hotels", "check_in_time_end")
    op.drop_column("hotel_crs_hotels", "hotel_chain")
    op.drop_column("hotel_crs_hotels", "accommodation_type_code")
    op.drop_column("hotel_crs_hotels", "accommodation_type")
