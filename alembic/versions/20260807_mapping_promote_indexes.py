"""add mapping promote/lookup indexes

Revision ID: 20260807_mapping_promote_indexes
Revises: 20260807_ratehawk_mapping_stream
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_mapping_promote_indexes"
down_revision: str | None = "20260807_ratehawk_mapping_stream"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Staging claim / promote progress (hotel + room workers)
    op.create_index(
        "ix_staging_hotels_run_rooms_claim",
        "staging_hotels",
        ["mapping_run_id", "hotel_promoted_at", "rooms_promoted_at", "extras_claimed_at"],
    )
    op.create_index(
        "ix_staging_hotels_dedupe_key",
        "staging_hotels",
        ["dedupe_key"],
    )
    op.create_index(
        "ix_staging_hotels_region_id",
        "staging_hotels",
        ["region_id"],
    )
    op.create_index(
        "ix_staging_rooms_run_hotel",
        "staging_rooms",
        ["mapping_run_id", "supplier_hotel_code"],
    )

    # Region map reverse lookup (catalogue id → rows); source+region covered by unique constraint
    op.create_index(
        "ix_booking_source_region_map_region",
        "booking_source_region_map",
        ["new_cities_n_region_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_booking_source_region_map_region", table_name="booking_source_region_map")
    op.drop_index("ix_staging_rooms_run_hotel", table_name="staging_rooms")
    op.drop_index("ix_staging_hotels_region_id", table_name="staging_hotels")
    op.drop_index("ix_staging_hotels_dedupe_key", table_name="staging_hotels")
    op.drop_index("ix_staging_hotels_run_rooms_claim", table_name="staging_hotels")
