"""drop legacy hotel search/markup city_id columns

Revision ID: 20260809_drop_legacy_city_id
Revises: 20260809_payment_refunds
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_drop_legacy_city_id"
down_revision: str | None = "20260809_payment_refunds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_hotel_searches_city_checkin_checkout")
    op.execute(
        "ALTER TABLE hotel_searches DROP CONSTRAINT IF EXISTS hotel_searches_city_id_fkey"
    )
    op.drop_column("hotel_searches", "city_id")
    op.create_index(
        "ix_hotel_searches_checkin_checkout",
        "hotel_searches",
        ["checkin_date", "checkout_date"],
    )

    op.drop_column("hotel_markup_rules", "city_id")


def downgrade() -> None:
    op.add_column(
        "hotel_markup_rules",
        sa.Column("city_id", sa.String(length=36), nullable=True),
    )

    op.drop_index("ix_hotel_searches_checkin_checkout", table_name="hotel_searches")
    op.add_column(
        "hotel_searches",
        sa.Column("city_id", sa.String(length=36), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_hotel_searches_city_checkin_checkout",
        "hotel_searches",
        ["city_id", "checkin_date", "checkout_date"],
    )
    op.alter_column("hotel_searches", "city_id", server_default=None)
