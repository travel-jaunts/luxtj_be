"""flight markup rules + hotel markup region_id

Revision ID: 20260809_markup_engines
Revises: 20260809_drop_legacy_city_id
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_markup_engines"
down_revision: str | None = "20260809_drop_legacy_city_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "flight_markup_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="inactive"),
        sa.Column("airline", sa.String(length=10), nullable=True),
        sa.Column("origin", sa.String(length=10), nullable=True),
        sa.Column("destination", sa.String(length=10), nullable=True),
        sa.Column("cabin_class", sa.String(length=40), nullable=True),
        sa.Column("travel_date_from", sa.Date(), nullable=True),
        sa.Column("travel_date_to", sa.Date(), nullable=True),
        sa.Column("markup_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("is_percentage", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_flight_markup_rules_status", "flight_markup_rules", ["status"])

    op.add_column(
        "hotel_markup_rules",
        sa.Column("region_id", sa.String(length=36), nullable=True),
    )
    op.create_index("ix_hotel_markup_rules_region_id", "hotel_markup_rules", ["region_id"])


def downgrade() -> None:
    op.drop_index("ix_hotel_markup_rules_region_id", table_name="hotel_markup_rules")
    op.drop_column("hotel_markup_rules", "region_id")
    op.drop_index("ix_flight_markup_rules_status", table_name="flight_markup_rules")
    op.drop_table("flight_markup_rules")
