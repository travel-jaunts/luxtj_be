"""replace profile stay booleans with accommodation types

Revision ID: 20260818_acct_accom_types
Revises: 20260816_account_profile
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_acct_accom_types"
down_revision: str | None = "20260816_account_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_TO_ACCOMMODATION_TYPE = {
    "stay_hotels": "Urban Luxury Hotels",
    "stay_villas": "Private Villas & Luxury Rentals",
    "stay_resorts": "Luxury Resorts",
    "stay_boutique_hotels": "Boutique Luxury Hotels",
    "stay_cruises": "Luxury Cruises / Floating Hotels",
}


def upgrade() -> None:
    op.add_column(
        "account_profiles",
        sa.Column("accommodation_types", sa.JSON(), nullable=False, server_default="[]"),
    )

    table = sa.table(
        "account_profiles",
        sa.column("account_id", sa.String()),
        sa.column("accommodation_types", sa.JSON()),
        *[sa.column(column_name, sa.Boolean()) for column_name in _LEGACY_TO_ACCOMMODATION_TYPE],
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            table.c.account_id,
            *(table.c[column_name] for column_name in _LEGACY_TO_ACCOMMODATION_TYPE),
        )
    )
    for row in rows:
        accommodation_types = [
            accommodation_type
            for column_name, accommodation_type in _LEGACY_TO_ACCOMMODATION_TYPE.items()
            if getattr(row, column_name)
        ]
        connection.execute(
            sa.update(table)
            .where(table.c.account_id == row.account_id)
            .values(accommodation_types=accommodation_types)
        )

    for column_name in _LEGACY_TO_ACCOMMODATION_TYPE:
        op.drop_column("account_profiles", column_name)


def downgrade() -> None:
    for column_name in _LEGACY_TO_ACCOMMODATION_TYPE:
        op.add_column(
            "account_profiles",
            sa.Column(column_name, sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    table = sa.table(
        "account_profiles",
        sa.column("account_id", sa.String()),
        sa.column("accommodation_types", sa.JSON()),
        *[sa.column(column_name, sa.Boolean()) for column_name in _LEGACY_TO_ACCOMMODATION_TYPE],
    )
    connection = op.get_bind()
    rows = connection.execute(sa.select(table.c.account_id, table.c.accommodation_types))
    for row in rows:
        selected_types = set(row.accommodation_types or [])
        connection.execute(
            sa.update(table)
            .where(table.c.account_id == row.account_id)
            .values(
                **{
                    column_name: accommodation_type in selected_types
                    for column_name, accommodation_type in _LEGACY_TO_ACCOMMODATION_TYPE.items()
                }
            )
        )

    op.drop_column("account_profiles", "accommodation_types")
