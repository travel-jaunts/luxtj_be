"""add profile banner image column

Revision ID: 20260827_account_profile_banner
Revises: 20260818_acct_accom_types
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_account_profile_banner"
down_revision: str | None = "20260818_acct_accom_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "account_profiles",
        sa.Column("profile_banner_image_id", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("account_profiles", "profile_banner_image_id")
