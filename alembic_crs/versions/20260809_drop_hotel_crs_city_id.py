"""drop legacy hotel_crs_hotels.city_id

Revision ID: 20260809_drop_hotel_crs_city_id
Revises: 20260807_crs_normalize_content
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_drop_hotel_crs_city_id"
down_revision: str | None = "20260807_crs_normalize_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_city_id_status")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_city_id_star_rating")
    op.execute("DROP INDEX IF EXISTS ix_hotel_crs_hotels_city_id")
    op.execute(
        "ALTER TABLE hotel_crs_hotels DROP CONSTRAINT IF EXISTS hotel_crs_hotels_city_id_fkey"
    )
    op.drop_column("hotel_crs_hotels", "city_id")


def downgrade() -> None:
    op.add_column(
        "hotel_crs_hotels",
        sa.Column("city_id", sa.String(length=36), nullable=True),
    )
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
