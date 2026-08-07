"""add integration registry tables

Revision ID: 20260807_integration_registry
Revises: 20260806_identity_auth
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_integration_registry"
down_revision: str | None = "20260806_identity_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "modules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "sub_modules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "booking_apis",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sub_module_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("api_type", sa.String(length=10), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sub_module_id"], ["sub_modules.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("sub_module_id", "code", name="uq_booking_apis_sub_module_code"),
    )
    op.create_index("ix_booking_apis_code", "booking_apis", ["code"])

    op.create_table(
        "payment_gateways",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("api_type", sa.String(length=10), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("convenience_type", sa.String(length=20), nullable=True),
        sa.Column("convenience_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "other_apis",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )


def downgrade() -> None:
    op.drop_table("other_apis")
    op.drop_table("payment_gateways")
    op.drop_index("ix_booking_apis_code", table_name="booking_apis")
    op.drop_table("booking_apis")
    op.drop_table("sub_modules")
    op.drop_table("modules")
