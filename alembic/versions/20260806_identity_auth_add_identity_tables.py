"""add identity auth tables

Revision ID: 20260806_identity_auth
Revises: 20260723_a7c8d9e0f1a2
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_identity_auth"
down_revision: str | None = "a7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resource", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_identity_permissions_code", "identity_permissions", ["code"])

    op.create_table(
        "identity_roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_identity_roles_name", "identity_roles", ["name"])

    op.create_table(
        "identity_role_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("permission_code", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["identity_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_code"], ["identity_permissions.code"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),
    )

    op.create_table(
        "identity_users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("user_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role_id", sa.String(length=36), nullable=True),
        sa.Column("password_reset_token_hash", sa.String(length=128), nullable=True),
        sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["identity_roles.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_identity_users_email", "identity_users", ["email"])
    op.create_index("ix_identity_users_user_type", "identity_users", ["user_type"])


def downgrade() -> None:
    op.drop_table("identity_users")
    op.drop_table("identity_role_permissions")
    op.drop_table("identity_roles")
    op.drop_table("identity_permissions")
