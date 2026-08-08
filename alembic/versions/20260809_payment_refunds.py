"""add payment refund columns

Revision ID: 20260809_payment_refunds
Revises: 20260808_flight_booking_core
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_payment_refunds"
down_revision: str | None = "20260808_flight_booking_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_gateway_transactions",
        sa.Column(
            "refunded_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "payment_gateway_transactions",
        sa.Column("refund_remark", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "payment_gateway_transactions",
        sa.Column("refund_mode", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "payment_gateway_transactions",
        sa.Column("refund_details", sa.JSON(), nullable=True),
    )
    op.add_column(
        "payment_gateway_transactions",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_payment_gateway_transactions_status",
        "payment_gateway_transactions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_gateway_transactions_status",
        table_name="payment_gateway_transactions",
    )
    op.drop_column("payment_gateway_transactions", "refunded_at")
    op.drop_column("payment_gateway_transactions", "refund_details")
    op.drop_column("payment_gateway_transactions", "refund_mode")
    op.drop_column("payment_gateway_transactions", "refund_remark")
    op.drop_column("payment_gateway_transactions", "refunded_amount")
