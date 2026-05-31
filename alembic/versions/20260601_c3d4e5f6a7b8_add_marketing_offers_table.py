"""add marketing_offers table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_offers",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("discount_value", sa.Float(), nullable=False),
        sa.Column("min_booking_value", sa.Float(), nullable=False),
        sa.Column("min_booking_value_currency", sa.String(8), nullable=False),
        sa.Column("validity_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validity_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_limit_per_user", sa.Integer(), nullable=True),
        sa.Column("applicability_on", sa.JSON(), nullable=False),
        sa.Column("stackable", sa.Boolean(), nullable=False),
        sa.Column("auto_apply", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_marketing_offers_status", "marketing_offers", ["status"])


def downgrade() -> None:
    op.drop_index("ix_marketing_offers_status", table_name="marketing_offers")
    op.drop_table("marketing_offers")
