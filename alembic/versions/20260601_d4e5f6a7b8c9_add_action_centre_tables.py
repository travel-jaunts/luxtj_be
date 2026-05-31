"""add action_centre tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_centre_items",
        sa.Column("workflow", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("workflow", "entity_id"),
    )
    op.create_index(
        "ix_action_centre_items_workflow_status",
        "action_centre_items",
        ["workflow", "status"],
    )

    op.create_table(
        "action_centre_outbox_cursor",
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("last_processed_outbox_id", sa.String(36), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("action_centre_outbox_cursor")
    op.drop_index("ix_action_centre_items_workflow_status", table_name="action_centre_items")
    op.drop_table("action_centre_items")
