"""CRS inventory search indexes for multi-million hotel catalogue.

Revision ID: 20260807_crs_inventory_indexes
Revises: 20260807_crs_region_defaults
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_crs_inventory_indexes"
down_revision: str | None = "20260807_crs_region_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Trigram indexes enable fast ILIKE '%term%' / contains search at scale.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_hotels_name_trgm
        ON hotel_crs_hotels
        USING gin (name_normalized gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_hotels_name_raw_trgm
        ON hotel_crs_hotels
        USING gin (name gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_hotels_address_line1_trgm
        ON hotel_crs_hotels
        USING gin (address_line1 gin_trgm_ops)
        WHERE address_line1 IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_hotels_location_trgm
        ON hotel_crs_hotels
        USING gin (location gin_trgm_ops)
        WHERE location IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_hotels_created_at_id
        ON hotel_crs_hotels (created_at DESC, id DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_hotels_status_created_at_id
        ON hotel_crs_hotels (status, created_at DESC, id DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_supplier_hotel_map_hotel_id
        ON hotel_crs_supplier_hotel_map (hotel_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_hotel_crs_room_amenity_map_room_group_id
        ON hotel_crs_room_amenity_map (room_group_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_room_amenity_map_room_group_id")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_supplier_hotel_map_hotel_id")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_status_created_at_id")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_created_at_id")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_location_trgm")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_address_line1_trgm")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_name_raw_trgm")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_name_trgm")
