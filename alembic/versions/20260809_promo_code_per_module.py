"""Allow same promo code across modules (drop marketing_offers.code unique).

Revision ID: 20260809_promo_code_per_module
Revises: 20260809_markup_engines
Create Date: 2026-08-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_promo_code_per_module"
down_revision: str | Sequence[str] | None = "20260809_markup_engines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Global unique blocked FLIGHT+HOTEL sharing the same promo code.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    uniques = inspector.get_unique_constraints("marketing_offers")
    for uc in uniques:
        cols = list(uc.get("column_names") or [])
        if cols == ["code"] or set(cols) == {"code"}:
            op.drop_constraint(uc["name"], "marketing_offers", type_="unique")
            break
    indexes = {ix["name"] for ix in inspector.get_indexes("marketing_offers")}
    if "ix_marketing_offers_code" not in indexes:
        op.create_index("ix_marketing_offers_code", "marketing_offers", ["code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_marketing_offers_code", table_name="marketing_offers")
    op.create_unique_constraint("marketing_offers_code_key", "marketing_offers", ["code"])
