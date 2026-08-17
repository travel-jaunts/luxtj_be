"""add account refresh sessions

Revision ID: 20260814_acct_refresh_sessions
Revises: 20260809_promo_code_per_module
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_acct_refresh_sessions"
down_revision: str | None = "20260809_promo_code_per_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_refresh_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("token_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replacement_token_id", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_id", name="uq_account_refresh_session_token_id"),
    )
    op.create_index(
        "ix_account_refresh_session_account",
        "account_refresh_sessions",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_account_refresh_session_expiry",
        "account_refresh_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_account_refresh_session_revoked",
        "account_refresh_sessions",
        ["revoked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_account_refresh_session_revoked", table_name="account_refresh_sessions")
    op.drop_index("ix_account_refresh_session_expiry", table_name="account_refresh_sessions")
    op.drop_index("ix_account_refresh_session_account", table_name="account_refresh_sessions")
    op.drop_table("account_refresh_sessions")
