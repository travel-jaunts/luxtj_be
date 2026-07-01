"""add customer bucket list tables

Revision ID: f6a7b8c9d0e1
Revises: e1f2a3b4c5d6
Create Date: 2026-07-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_bucket_lists",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_bucket_lists_account_id",
        "customer_bucket_lists",
        ["account_id"],
        unique=True,
    )

    op.create_table(
        "customer_bucket_list_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("bucket_list_id", sa.String(36), nullable=False),
        sa.Column("destination_kind", sa.String(16), nullable=False),
        sa.Column("destination_name", sa.String(255), nullable=False),
        sa.Column("normalized_destination_name", sa.String(255), nullable=False),
        sa.Column("parent_country", sa.String(255), nullable=True),
        sa.Column("ideal_days", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["bucket_list_id"], ["customer_bucket_lists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bucket_list_id",
            "destination_kind",
            "normalized_destination_name",
            "is_active",
            name="uq_customer_bucket_active_destination",
        ),
        sa.CheckConstraint("ideal_days > 0", name="ck_customer_bucket_ideal_days_positive"),
    )
    op.create_index(
        "ix_customer_bucket_list_items_bucket_list_id",
        "customer_bucket_list_items",
        ["bucket_list_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_bucket_list_items_is_active",
        "customer_bucket_list_items",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_customer_bucket_items_lookup",
        "customer_bucket_list_items",
        ["bucket_list_id", "is_active", "display_order"],
        unique=False,
    )
    op.create_index(
        "ix_customer_bucket_items_destination_search",
        "customer_bucket_list_items",
        ["destination_kind", "normalized_destination_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customer_bucket_items_destination_search", table_name="customer_bucket_list_items")
    op.drop_index("ix_customer_bucket_items_lookup", table_name="customer_bucket_list_items")
    op.drop_index("ix_customer_bucket_list_items_is_active", table_name="customer_bucket_list_items")
    op.drop_index("ix_customer_bucket_list_items_bucket_list_id", table_name="customer_bucket_list_items")
    op.drop_table("customer_bucket_list_items")

    op.drop_index("ix_customer_bucket_lists_account_id", table_name="customer_bucket_lists")
    op.drop_table("customer_bucket_lists")
