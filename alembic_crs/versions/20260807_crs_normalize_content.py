"""CRS Alembic: normalize RateHawk JSON blobs into generic columns/tables.

Revision ID: 20260807_crs_normalize_content
Revises: 20260807_crs_ratehawk_content
Create Date: 2026-08-07

Supplier-agnostic hotel/room content storage — no JSON blobs on CRS hotels/rooms.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
    table_exists,
)

revision: str = "20260807_crs_normalize_content"
down_revision: str | None = "20260807_crs_ratehawk_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- hotel_crs_hotels: flat columns replacing JSON blobs ---
    add_column_if_missing(
        "hotel_crs_hotels", sa.Column("floors_count", sa.SmallInteger(), nullable=True)
    )
    add_column_if_missing("hotel_crs_hotels", sa.Column("rooms_count", sa.Integer(), nullable=True))
    add_column_if_missing(
        "hotel_crs_hotels", sa.Column("year_built", sa.SmallInteger(), nullable=True)
    )
    add_column_if_missing(
        "hotel_crs_hotels", sa.Column("year_renovated", sa.SmallInteger(), nullable=True)
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("electricity_frequency", sa.String(length=100), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("electricity_voltage", sa.String(length=100), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("electricity_sockets", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("star_certificate_id", sa.String(length=100), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("star_certificate_valid_to", sa.String(length=40), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup_type", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup_phone", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup_email", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup_is_contactless", sa.Boolean(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup_address", sa.String(length=500), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup_extra_info", sa.Text(), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_record", sa.String(length=100), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_link", sa.String(length=2048), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_email", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_phone", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_status", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_kind", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_name", sa.String(length=255), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_address", sa.String(length=500), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_status_end_date", sa.String(length=40), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_taxpayer_number", sa.String(length=30), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column(
            "register_state_registration_number",
            sa.String(length=30),
            nullable=True,
        ),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("register_work_time", sa.String(length=255), nullable=True),
    )
    # Prefer generic name for supplier legacy id (keep supplier_slug for now; add alias col)
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("external_code", sa.String(length=255), nullable=True),
    )

    drop_column_if_exists("hotel_crs_hotels", "meta")
    drop_column_if_exists("hotel_crs_hotels", "description_struct")
    drop_column_if_exists("hotel_crs_hotels", "facts")
    drop_column_if_exists("hotel_crs_hotels", "keys_pickup")
    drop_column_if_exists("hotel_crs_hotels", "star_certificate")
    drop_column_if_exists("hotel_crs_hotels", "payment_methods")
    drop_column_if_exists("hotel_crs_hotels", "serp_filters")

    # --- hotel_crs_room_groups: expand codes → labels; drop JSON ---
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("gender", sa.String(length=30), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups", sa.Column("is_family", sa.Boolean(), nullable=True)
    )
    add_column_if_missing(
        "hotel_crs_room_groups", sa.Column("is_club", sa.Boolean(), nullable=True)
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("floor_type", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("view_type", sa.String(length=80), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("class_label", sa.String(length=50), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("quality_label", sa.String(length=50), nullable=True),
    )
    drop_column_if_exists("hotel_crs_room_groups", "name_struct")
    drop_column_if_exists("hotel_crs_room_groups", "rg_ext")
    drop_column_if_exists("hotel_crs_room_groups", "raw")

    # --- description sections ---
    if not table_exists("hotel_crs_hotel_description_sections"):
        op.create_table(
            "hotel_crs_hotel_description_sections",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_description_sections_hotel_id",
        "hotel_crs_hotel_description_sections",
        ["hotel_id"],
    )

    # --- payment methods ---
    if not table_exists("hotel_crs_hotel_payment_methods"):
        op.create_table(
            "hotel_crs_hotel_payment_methods",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), nullable=False),
            sa.Column("method_code", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "hotel_id", "method_code", name="uq_hotel_crs_hotel_payment_methods"
            ),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_payment_methods_hotel_id",
        "hotel_crs_hotel_payment_methods",
        ["hotel_id"],
    )

    # --- feature tags (was serp_filters) ---
    if not table_exists("hotel_crs_hotel_feature_tags"):
        op.create_table(
            "hotel_crs_hotel_feature_tags",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), nullable=False),
            sa.Column("tag", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("hotel_id", "tag", name="uq_hotel_crs_hotel_feature_tags"),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_feature_tags_hotel_id",
        "hotel_crs_hotel_feature_tags",
        ["hotel_id"],
    )

    # --- policy narrative sections (policy_struct + extra info) ---
    if not table_exists("hotel_crs_hotel_policy_sections"):
        op.create_table(
            "hotel_crs_hotel_policy_sections",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), nullable=False),
            sa.Column("section_type", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_policy_sections_hotel_id",
        "hotel_crs_hotel_policy_sections",
        ["hotel_id"],
    )

    # --- structured policy fee/rule items (metapolicy) ---
    if not table_exists("hotel_crs_hotel_policy_items"):
        op.create_table(
            "hotel_crs_hotel_policy_items",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_policy_items_hotel_id",
        "hotel_crs_hotel_policy_items",
        ["hotel_id"],
    )
    create_index_if_missing(
        "ix_hotel_crs_hotel_policy_items_hotel_category",
        "hotel_crs_hotel_policy_items",
        ["hotel_id", "category"],
    )

    if not table_exists("hotel_crs_hotel_policy_item_attrs"):
        op.create_table(
            "hotel_crs_hotel_policy_item_attrs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("policy_item_id", sa.String(length=36), nullable=False),
            sa.Column("attr_key", sa.String(length=80), nullable=False),
            sa.Column("attr_value", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["policy_item_id"],
                ["hotel_crs_hotel_policy_items.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "policy_item_id",
                "attr_key",
                name="uq_hotel_crs_hotel_policy_item_attrs",
            ),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_policy_item_attrs_item_id",
        "hotel_crs_hotel_policy_item_attrs",
        ["policy_item_id"],
    )

    # --- register room categories (FSA / local register) ---
    if not table_exists("hotel_crs_hotel_register_room_categories"):
        op.create_table(
            "hotel_crs_hotel_register_room_categories",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), nullable=False),
            sa.Column("category_type", sa.String(length=100), nullable=True),
            sa.Column("rooms_count", sa.Integer(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["hotel_id"], ["hotel_crs_hotels.id"], ondelete="CASCADE"),
        )
    create_index_if_missing(
        "ix_hotel_crs_hotel_register_room_categories_hotel_id",
        "hotel_crs_hotel_register_room_categories",
        ["hotel_id"],
    )


def downgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_register_room_categories CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_policy_item_attrs CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_policy_items CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_policy_sections CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_feature_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_payment_methods CASCADE")
    op.execute("DROP TABLE IF EXISTS hotel_crs_hotel_description_sections CASCADE")

    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("rg_ext", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_room_groups",
        sa.Column("name_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    drop_column_if_exists("hotel_crs_room_groups", "quality_label")
    drop_column_if_exists("hotel_crs_room_groups", "class_label")
    drop_column_if_exists("hotel_crs_room_groups", "view_type")
    drop_column_if_exists("hotel_crs_room_groups", "floor_type")
    drop_column_if_exists("hotel_crs_room_groups", "is_club")
    drop_column_if_exists("hotel_crs_room_groups", "is_family")
    drop_column_if_exists("hotel_crs_room_groups", "gender")

    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("serp_filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("payment_methods", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("star_certificate", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("keys_pickup", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("description_struct", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add_column_if_missing(
        "hotel_crs_hotels",
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    for col in (
        "external_code",
        "register_work_time",
        "register_state_registration_number",
        "register_taxpayer_number",
        "register_status_end_date",
        "register_address",
        "register_name",
        "register_kind",
        "register_status",
        "register_phone",
        "register_email",
        "register_link",
        "register_record",
        "keys_pickup_extra_info",
        "keys_pickup_address",
        "keys_pickup_is_contactless",
        "keys_pickup_email",
        "keys_pickup_phone",
        "keys_pickup_type",
        "star_certificate_valid_to",
        "star_certificate_id",
        "electricity_sockets",
        "electricity_voltage",
        "electricity_frequency",
        "year_renovated",
        "year_built",
        "rooms_count",
        "floors_count",
    ):
        drop_column_if_exists("hotel_crs_hotels", col)
