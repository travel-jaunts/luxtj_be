"""add customer personal calendar tables

Revision ID: 9a8b7c6d5e4f
Revises: f6a7b8c9d0e1
Create Date: 2026-07-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9a8b7c6d5e4f"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_personal_calendars",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_personal_calendars_account_id",
        "customer_personal_calendars",
        ["account_id"],
        unique=True,
    )

    op.create_table(
        "customer_personal_calendar_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("calendar_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("birthday_for", sa.String(64), nullable=True),
        sa.Column("anniversary_for", sa.String(64), nullable=True),
        sa.Column("person_name", sa.String(255), nullable=True),
        sa.Column("person1_name", sa.String(255), nullable=True),
        sa.Column("person2_name", sa.String(255), nullable=True),
        sa.Column("event_name", sa.String(255), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("holiday_types", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('birthday', 'anniversary', 'special_occasion')",
            name="ck_customer_personal_calendar_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["calendar_id"], ["customer_personal_calendars.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_personal_calendar_events_calendar_id",
        "customer_personal_calendar_events",
        ["calendar_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_personal_calendar_events_event_date",
        "customer_personal_calendar_events",
        ["event_date"],
        unique=False,
    )

    op.create_table(
        "customer_personal_calendar_periods",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("calendar_id", sa.String(36), nullable=False),
        sa.Column("period_name", sa.String(255), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("is_date_flexible", sa.Boolean(), nullable=False),
        sa.Column("holiday_types", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "period_end >= period_start",
            name="ck_customer_personal_calendar_period_range",
        ),
        sa.ForeignKeyConstraint(
            ["calendar_id"], ["customer_personal_calendars.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_personal_calendar_periods_calendar_id",
        "customer_personal_calendar_periods",
        ["calendar_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_personal_calendar_periods_start_end",
        "customer_personal_calendar_periods",
        ["period_start", "period_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_personal_calendar_periods_start_end",
        table_name="customer_personal_calendar_periods",
    )
    op.drop_index(
        "ix_customer_personal_calendar_periods_calendar_id",
        table_name="customer_personal_calendar_periods",
    )
    op.drop_table("customer_personal_calendar_periods")

    op.drop_index(
        "ix_customer_personal_calendar_events_event_date",
        table_name="customer_personal_calendar_events",
    )
    op.drop_index(
        "ix_customer_personal_calendar_events_calendar_id",
        table_name="customer_personal_calendar_events",
    )
    op.drop_table("customer_personal_calendar_events")

    op.drop_index(
        "ix_customer_personal_calendars_account_id",
        table_name="customer_personal_calendars",
    )
    op.drop_table("customer_personal_calendars")
