"""add server defaults on region_mapping_runs counters

Revision ID: 20260807_crs_region_defaults
Revises: 20260807_crs_initial
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_crs_region_defaults"
down_revision: str | None = "20260807_crs_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE region_mapping_runs "
        "ALTER COLUMN processed_count SET DEFAULT 0, "
        "ALTER COLUMN matched_count SET DEFAULT 0, "
        "ALTER COLUMN skipped_count SET DEFAULT 0, "
        "ALTER COLUMN cities_count SET DEFAULT 0, "
        "ALTER COLUMN source SET DEFAULT 'admin', "
        "ALTER COLUMN status SET DEFAULT 'pending'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE region_mapping_runs "
        "ALTER COLUMN processed_count DROP DEFAULT, "
        "ALTER COLUMN matched_count DROP DEFAULT, "
        "ALTER COLUMN skipped_count DROP DEFAULT, "
        "ALTER COLUMN cities_count DROP DEFAULT, "
        "ALTER COLUMN source DROP DEFAULT, "
        "ALTER COLUMN status DROP DEFAULT"
    )
