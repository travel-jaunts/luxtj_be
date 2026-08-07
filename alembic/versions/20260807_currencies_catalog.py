"""add currencies catalog table

Revision ID: 20260807_currencies_catalog
Revises: 20260807_hotel_crs_booking_core
Create Date: 2026-08-07
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_currencies_catalog"
down_revision: str | None = "20260807_hotel_crs_booking_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    currencies = op.create_table(
        "currencies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_currencies_code"),
    )

    # Backfill from distinct country currency metadata when present.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT
                upper(trim(currency_code)) AS code,
                min(currency_name) AS name,
                coalesce(min(nullif(currency_symbol, '')), '') AS symbol
            FROM countries
            WHERE currency_code IS NOT NULL
              AND length(trim(currency_code)) = 3
            GROUP BY upper(trim(currency_code))
            """
        )
    ).mappings().all()
    now = datetime.now(UTC)
    if rows:
        op.bulk_insert(
            currencies,
            [
                {
                    "id": str(uuid4()),
                    "code": row["code"],
                    "name": row["name"] or row["code"],
                    "symbol": row["symbol"] or "",
                    "created_at": now,
                    "updated_at": now,
                }
                for row in rows
            ],
        )


def downgrade() -> None:
    op.drop_table("currencies")
