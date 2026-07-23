"""add deleted_at to customer personal calendar item tables

Revision ID: a7c8d9e0f1a2
Revises: 9a8b7c6d5e4f
Create Date: 2026-07-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c8d9e0f1a2"
down_revision: str | None = "9a8b7c6d5e4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_personal_calendar_events",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_customer_personal_calendar_events_deleted_at",
        "customer_personal_calendar_events",
        ["deleted_at"],
        unique=False,
    )
    op.add_column(
        "customer_personal_calendar_periods",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_customer_personal_calendar_periods_deleted_at",
        "customer_personal_calendar_periods",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_personal_calendar_periods_deleted_at",
        table_name="customer_personal_calendar_periods",
    )
    op.drop_column("customer_personal_calendar_periods", "deleted_at")
    op.drop_index(
        "ix_customer_personal_calendar_events_deleted_at",
        table_name="customer_personal_calendar_events",
    )
    op.drop_column("customer_personal_calendar_events", "deleted_at")
