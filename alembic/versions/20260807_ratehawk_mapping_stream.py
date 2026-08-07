"""add ratehawk region/hotel stream mapping tables

Revision ID: 20260807_ratehawk_mapping_stream
Revises: 20260807_currencies_catalog
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_ratehawk_mapping_stream"
down_revision: str | None = "20260807_currencies_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "new_cities_n_regions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, server_default="Unknown"),
        sa.Column("iata", sa.String(length=3), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("country_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default=""),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_new_cities_n_regions_dedupe_key"),
    )
    op.create_index("ix_new_cities_n_regions_country_code", "new_cities_n_regions", ["country_code"])
    op.create_index("ix_new_cities_n_regions_name", "new_cities_n_regions", ["name"])

    op.create_table(
        "booking_source_region_map",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("booking_source_id", sa.String(length=36), nullable=False),
        sa.Column("new_cities_n_region_id", sa.String(length=36), nullable=False),
        sa.Column("booking_source_region_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_source_id"], ["booking_apis.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["new_cities_n_region_id"], ["new_cities_n_regions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "booking_source_id",
            "booking_source_region_code",
            name="uq_booking_source_region_map_code",
        ),
        sa.UniqueConstraint(
            "booking_source_id",
            "new_cities_n_region_id",
            name="uq_booking_source_region_map_region",
        ),
    )
    op.create_index(
        "ix_booking_source_region_map_source",
        "booking_source_region_map",
        ["booking_source_id"],
    )

    op.create_table(
        "region_mapping_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("booking_source_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="admin"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("dump_url", sa.Text(), nullable=True),
        sa.Column("zst_path", sa.Text(), nullable=True),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cities_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_source_id"], ["booking_apis.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_region_mapping_runs_source_status",
        "region_mapping_runs",
        ["booking_source_id", "status"],
    )

    op.create_table(
        "hotel_mapping_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("booking_source_id", sa.String(length=36), nullable=False),
        sa.Column("parent_run_id", sa.String(length=36), nullable=True),
        sa.Column("dump_type", sa.String(length=30), nullable=False, server_default="full"),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="admin"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("dump_url", sa.Text(), nullable=True),
        sa.Column("zst_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_source_id"], ["booking_apis.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_run_id"], ["hotel_mapping_runs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_hotel_mapping_runs_source_status",
        "hotel_mapping_runs",
        ["booking_source_id", "status"],
    )

    op.create_table(
        "staging_hotels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("mapping_run_id", sa.String(length=36), nullable=False),
        sa.Column("shard_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("supplier_hotel_code", sa.String(length=64), nullable=False),
        sa.Column("dedupe_key", sa.String(length=32), nullable=False),
        sa.Column("region_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=30), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("star_rating", sa.Numeric(3, 1), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("phone", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("image", sa.String(length=2048), nullable=True),
        sa.Column("amenity_names", sa.JSON(), nullable=True),
        sa.Column("image_urls", sa.JSON(), nullable=True),
        sa.Column("room_payload", sa.JSON(), nullable=True),
        sa.Column("policy_payload", sa.JSON(), nullable=True),
        sa.Column("hotel_promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rooms_promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promote_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extras_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mapping_run_id"], ["hotel_mapping_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["new_cities_n_regions.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_staging_hotels_run_promote",
        "staging_hotels",
        ["mapping_run_id", "hotel_promoted_at", "promote_claimed_at"],
    )
    op.create_index(
        "ix_staging_hotels_run_code",
        "staging_hotels",
        ["mapping_run_id", "supplier_hotel_code"],
    )

    op.create_table(
        "staging_rooms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("mapping_run_id", sa.String(length=36), nullable=False),
        sa.Column("shard_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("supplier_hotel_code", sa.String(length=64), nullable=False),
        sa.Column("room_group_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amenity_slugs", sa.JSON(), nullable=True),
        sa.Column("image_urls", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mapping_run_id"], ["hotel_mapping_runs.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "mapping_run_id",
            "supplier_hotel_code",
            "room_group_id",
            name="uq_staging_rooms_run_hotel_room",
        ),
    )

    # CRS hotels: region support + phone widen
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("region_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_hotel_crs_hotels_region_id",
        "hotel_crs_hotels",
        "new_cities_n_regions",
        ["region_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column(
        "hotel_crs_hotels",
        "city_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.alter_column(
        "hotel_crs_hotels",
        "phone",
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.create_index("ix_hotel_crs_hotels_region_id", "hotel_crs_hotels", ["region_id"])
    op.create_index(
        "ix_hotel_crs_hotels_region_id_star_rating",
        "hotel_crs_hotels",
        ["region_id", "star_rating"],
    )
    op.create_index(
        "ix_hotel_crs_hotels_region_id_status",
        "hotel_crs_hotels",
        ["region_id", "status"],
    )

    # Allow hotel_searches.city_id to store catalogue region ids (Path B).
    op.execute("ALTER TABLE hotel_searches DROP CONSTRAINT IF EXISTS hotel_searches_city_id_fkey")


def downgrade() -> None:
    op.drop_index("ix_hotel_crs_hotels_region_id_status", table_name="hotel_crs_hotels")
    op.drop_index("ix_hotel_crs_hotels_region_id_star_rating", table_name="hotel_crs_hotels")
    op.drop_index("ix_hotel_crs_hotels_region_id", table_name="hotel_crs_hotels")
    op.drop_constraint("fk_hotel_crs_hotels_region_id", "hotel_crs_hotels", type_="foreignkey")
    op.drop_column("hotel_crs_hotels", "region_id")
    op.alter_column(
        "hotel_crs_hotels",
        "phone",
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
    op.alter_column(
        "hotel_crs_hotels",
        "city_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.create_foreign_key(
        "hotel_searches_city_id_fkey",
        "hotel_searches",
        "cities",
        ["city_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_table("staging_rooms")
    op.drop_index("ix_staging_hotels_run_code", table_name="staging_hotels")
    op.drop_index("ix_staging_hotels_run_promote", table_name="staging_hotels")
    op.drop_table("staging_hotels")
    op.drop_index("ix_hotel_mapping_runs_source_status", table_name="hotel_mapping_runs")
    op.drop_table("hotel_mapping_runs")
    op.drop_index("ix_region_mapping_runs_source_status", table_name="region_mapping_runs")
    op.drop_table("region_mapping_runs")
    op.drop_index("ix_booking_source_region_map_source", table_name="booking_source_region_map")
    op.drop_table("booking_source_region_map")
    op.drop_index("ix_new_cities_n_regions_name", table_name="new_cities_n_regions")
    op.drop_index("ix_new_cities_n_regions_country_code", table_name="new_cities_n_regions")
    op.drop_table("new_cities_n_regions")
