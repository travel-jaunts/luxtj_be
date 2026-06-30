"""add account auth tables

Revision ID: e1f2a3b4c5d6
Revises: b0682c3db2c7
Create Date: 2026-06-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "b0682c3db2c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_accounts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("dial_code", sa.String(8), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dial_code", "phone_number", name="uq_account_identity"),
    )
    op.create_index(
        "ix_account_identity",
        "account_accounts",
        ["dial_code", "phone_number"],
        unique=False,
    )

    op.create_table(
        "account_otp_challenges",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("dial_code", sa.String(8), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("flow_type", sa.String(16), nullable=False),
        sa.Column("otp_hash", sa.Text(), nullable=False),
        sa.Column("otp_salt", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts_left", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_otp_lookup",
        "account_otp_challenges",
        ["dial_code", "phone_number", "flow_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_otp_lookup", table_name="account_otp_challenges")
    op.drop_table("account_otp_challenges")

    op.drop_index("ix_account_identity", table_name="account_accounts")
    op.drop_table("account_accounts")
