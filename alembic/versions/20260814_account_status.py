"""add account status

Revision ID: 20260814_acct_status
Revises: 20260814_acct_refresh_sessions
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_acct_status"
down_revision: str | None = "20260814_acct_refresh_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "account_accounts",
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
    )
    op.create_index("ix_account_accounts_status", "account_accounts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_account_accounts_status", table_name="account_accounts")
    op.drop_column("account_accounts", "status")
