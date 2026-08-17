"""add account status history

Revision ID: 20260814_acct_status_history
Revises: 20260814_acct_status
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_acct_status_history"
down_revision: str | None = "20260814_acct_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_status_changes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=False),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_status_changes_account",
        "account_status_changes",
        ["account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_account_status_changes_account", table_name="account_status_changes")
    op.drop_table("account_status_changes")
