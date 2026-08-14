"""add flight search and booking tables

Revision ID: 20260808_flight_booking_core
Revises: 20260807_crs_db_split
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_flight_booking_core"
down_revision: str | None = "20260807_crs_db_split"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "flight_searches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("trip_type", sa.String(length=20), nullable=False),
        sa.Column("cabin_class", sa.String(length=30), nullable=False),
        sa.Column("adult_count", sa.Integer(), nullable=False),
        sa.Column("child_count", sa.Integer(), nullable=False),
        sa.Column("infant_count", sa.Integer(), nullable=False),
        sa.Column("search_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_flight_searches_created_at", "flight_searches", ["created_at"])

    op.create_table(
        "flight_booking_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("booking_source", sa.String(length=50), nullable=False),
        sa.Column("booking_id", sa.String(length=100), nullable=True),
        sa.Column("book_guid", sa.String(length=64), nullable=True),
        sa.Column("gdspnr", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("trip_type", sa.String(length=20), nullable=False),
        sa.Column("cabin_class", sa.String(length=30), nullable=True),
        sa.Column("origin", sa.String(length=10), nullable=True),
        sa.Column("destination", sa.String(length=10), nullable=True),
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("details_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("app_reference"),
    )
    op.create_index(
        "ix_flight_booking_details_booking_source",
        "flight_booking_details",
        ["booking_source"],
    )
    op.create_index("ix_flight_booking_details_status", "flight_booking_details", ["status"])
    op.create_index(
        "ix_flight_booking_details_created_by_id",
        "flight_booking_details",
        ["created_by_id"],
    )

    op.create_table(
        "flight_booking_transaction_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("basic_fare", sa.Numeric(14, 2), nullable=False),
        sa.Column("airline_tax", sa.Numeric(14, 2), nullable=False),
        sa.Column("admin_markup", sa.Numeric(14, 2), nullable=False),
        sa.Column("admin_discount", sa.Numeric(14, 2), nullable=False),
        sa.Column("promocode", sa.String(length=50), nullable=True),
        sa.Column("discount_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("convenience_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_fare", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("currency_conversion_rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("payment_mode", sa.String(length=50), nullable=True),
        sa.Column("pax_wise_fare_breakdown", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["app_reference"],
            ["flight_booking_details.app_reference"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("app_reference"),
    )
    op.create_index(
        "ix_flight_booking_txn_app_reference",
        "flight_booking_transaction_details",
        ["app_reference"],
    )

    op.create_table(
        "flight_booking_itinerary_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("rph", sa.Integer(), nullable=False),
        sa.Column("airline_code", sa.String(length=10), nullable=True),
        sa.Column("flight_number", sa.String(length=20), nullable=True),
        sa.Column("origin", sa.String(length=10), nullable=True),
        sa.Column("destination", sa.String(length=10), nullable=True),
        sa.Column("departure_datetime", sa.String(length=40), nullable=True),
        sa.Column("arrival_datetime", sa.String(length=40), nullable=True),
        sa.Column("cabin_class", sa.String(length=30), nullable=True),
        sa.Column("pnr", sa.String(length=50), nullable=True),
        sa.Column("segment_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["app_reference"],
            ["flight_booking_details.app_reference"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_flight_itinerary_app_reference",
        "flight_booking_itinerary_details",
        ["app_reference"],
    )

    op.create_table(
        "flight_booking_passenger_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_reference", sa.String(length=60), nullable=False),
        sa.Column("pass_guid", sa.String(length=64), nullable=True),
        sa.Column("age_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=20), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("date_of_birth", sa.String(length=20), nullable=True),
        sa.Column("nationality", sa.String(length=3), nullable=True),
        sa.Column("document_number", sa.String(length=50), nullable=True),
        sa.Column("document_expiry", sa.String(length=20), nullable=True),
        sa.Column("ticket_number", sa.String(length=50), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["app_reference"],
            ["flight_booking_details.app_reference"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_flight_pax_app_reference",
        "flight_booking_passenger_details",
        ["app_reference"],
    )


def downgrade() -> None:
    op.drop_index("ix_flight_pax_app_reference", table_name="flight_booking_passenger_details")
    op.drop_table("flight_booking_passenger_details")
    op.drop_index(
        "ix_flight_itinerary_app_reference", table_name="flight_booking_itinerary_details"
    )
    op.drop_table("flight_booking_itinerary_details")
    op.drop_index(
        "ix_flight_booking_txn_app_reference",
        table_name="flight_booking_transaction_details",
    )
    op.drop_table("flight_booking_transaction_details")
    op.drop_index("ix_flight_booking_details_created_by_id", table_name="flight_booking_details")
    op.drop_index("ix_flight_booking_details_status", table_name="flight_booking_details")
    op.drop_index("ix_flight_booking_details_booking_source", table_name="flight_booking_details")
    op.drop_table("flight_booking_details")
    op.drop_index("ix_flight_searches_created_at", table_name="flight_searches")
    op.drop_table("flight_searches")
