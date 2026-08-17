"""add account profile, travellers, albums and gallery images

Revision ID: 20260816_account_profile
Revises: 20260814_acct_status_history
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_account_profile"
down_revision: str | None = "20260814_acct_status_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_profiles",
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=True),
        sa.Column("last_name", sa.String(120), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(120), nullable=True),
        # Free-text location snapshot. A city_id FK can be added later without an API change.
        sa.Column("city_name", sa.String(200), nullable=True),
        sa.Column("country_code", sa.String(8), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("facebook_url", sa.String(500), nullable=True),
        sa.Column("instagram_url", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("alt_dial_code", sa.String(8), nullable=True),
        sa.Column("alt_phone_number", sa.String(32), nullable=True),
        sa.Column(
            "preferred_contact_method", sa.String(16), nullable=False, server_default="phone"
        ),
        sa.Column("emergency_contact_first_name", sa.String(120), nullable=True),
        sa.Column("emergency_contact_dial_code", sa.String(8), nullable=True),
        sa.Column("emergency_contact_phone_number", sa.String(32), nullable=True),
        sa.Column("stay_hotels", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stay_villas", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stay_resorts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stay_boutique_hotels", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stay_cruises", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("flight_class", sa.String(24), nullable=False, server_default="economy"),
        sa.Column("flight_priority", sa.String(24), nullable=False, server_default="best_value"),
        sa.Column("trip_pace", sa.String(24), nullable=False, server_default="balanced"),
        sa.Column("baggage_style", sa.String(24), nullable=False, server_default="light_packer"),
        # Free-text lists for now; a catalog-backed table can replace these later.
        sa.Column("countries_visited", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("indian_states_visited", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("places_loved", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("places_recommended", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("travel_moments_enjoyed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tier", sa.String(16), nullable=False, server_default="Novus"),
        sa.Column("badges", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("profile_picture_image_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("account_id"),
    )

    op.create_table(
        "account_profile_travellers",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=True),
        sa.Column("relationship", sa.String(60), nullable=True),
        sa.Column("nationality", sa.String(120), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        # Month and year only; the day is always pinned to 1.
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("passport_number_encrypted", sa.Text(), nullable=True),
        sa.Column("passport_last4", sa.String(4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_profile_traveller_account", "account_profile_travellers", ["account_id"]
    )

    op.create_table(
        "account_albums",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="private"),
        sa.Column("cover_image_id", sa.String(36), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_album_account", "account_albums", ["account_id"])
    op.create_index(
        "uq_account_album_system_kind",
        "account_albums",
        ["account_id", "kind"],
        unique=True,
        postgresql_where=sa.text("kind <> 'user'"),
        sqlite_where=sa.text("kind <> 'user'"),
    )

    op.create_table(
        "account_gallery_images",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("album_id", sa.String(36), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("city_name", sa.String(200), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_gallery_image_account", "account_gallery_images", ["account_id"])
    op.create_index("ix_account_gallery_image_album", "account_gallery_images", ["album_id"])


def downgrade() -> None:
    op.drop_index("ix_account_gallery_image_album", table_name="account_gallery_images")
    op.drop_index("ix_account_gallery_image_account", table_name="account_gallery_images")
    op.drop_table("account_gallery_images")

    op.drop_index("uq_account_album_system_kind", table_name="account_albums")
    op.drop_index("ix_account_album_account", table_name="account_albums")
    op.drop_table("account_albums")

    op.drop_index("ix_account_profile_traveller_account", table_name="account_profile_travellers")
    op.drop_table("account_profile_travellers")

    op.drop_table("account_profiles")
