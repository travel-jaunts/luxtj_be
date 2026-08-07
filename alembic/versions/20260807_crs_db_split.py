"""split crs/regions to separate db; booking uses hotel/room codes

Revision ID: 20260807_crs_db_split
Revises: 20260807_mapping_promote_indexes
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_crs_db_split"
down_revision: str | None = "20260807_mapping_promote_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Booking tables: replace CRS FK id with soft hotel/room codes ---
    op.execute(
        "ALTER TABLE hotel_booking_details "
        "DROP CONSTRAINT IF EXISTS hotel_booking_details_hotel_crs_hotel_id_fkey"
    )
    op.drop_index(
        "ix_hotel_booking_details_hotel_crs_hotel_id",
        table_name="hotel_booking_details",
    )
    op.drop_column("hotel_booking_details", "hotel_crs_hotel_id")
    op.add_column(
        "hotel_booking_details",
        sa.Column("hotel_crs_hotel_code", sa.String(length=30), nullable=True),
    )
    op.create_index(
        "ix_hotel_booking_details_hotel_crs_hotel_code",
        "hotel_booking_details",
        ["hotel_crs_hotel_code"],
    )

    op.add_column(
        "hotel_booking_itinerary_details",
        sa.Column("hotel_crs_room_code", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_hotel_booking_itinerary_details_hotel_crs_room_code",
        "hotel_booking_itinerary_details",
        ["hotel_crs_room_code"],
    )

    # --- Drop CRS / region / staging tables from main DB ---
    op.execute("DROP TABLE IF EXISTS staging_rooms CASCADE")
    op.execute("DROP TABLE IF EXISTS staging_hotels CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_mapping_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS region_mapping_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS booking_source_region_map CASCADE")

    op.execute("DROP TABLE IF EXISTS hotel_crs_room_amenity_map CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_room_images CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_room_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_amenity_map CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_images CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_supplier_hotel_map CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_amenities CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotels CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_suppliers CASCADE")
    op.execute("DROP TABLE IF EXISTS new_cities_n_regions CASCADE")


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade of CRS DB split is not supported — restore from backup / re-run CRS alembic."
    )
