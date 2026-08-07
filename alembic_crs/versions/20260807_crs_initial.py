"""initial hotel crs + regions schema

Revision ID: 20260807_crs_initial
Revises:
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_crs_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import CrsBase

    CrsBase.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import CrsBase

    CrsBase.metadata.drop_all(bind=op.get_bind())
