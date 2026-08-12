"""Idempotent helpers for CRS Alembic migrations.

`20260807_crs_initial` uses ``CrsBase.metadata.create_all()``, which creates the
*current* ORM schema. Later revisions must tolerate columns/tables/indexes that
already exist (fresh installs) while still applying changes on older DBs.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def table_exists(table: str) -> bool:
    return table in _inspector().get_table_names()


def column_exists(table: str, column: str) -> bool:
    if not table_exists(table):
        return False
    return any(c["name"] == column for c in _inspector().get_columns(table))


def index_exists(table: str, index_name: str) -> bool:
    if not table_exists(table):
        return False
    return any(i["name"] == index_name for i in _inspector().get_indexes(table))


def add_column_if_missing(table: str, column: sa.Column) -> None:
    if not column_exists(table, column.name):
        op.add_column(table, column)


def drop_column_if_exists(table: str, column: str) -> None:
    if column_exists(table, column):
        op.drop_column(table, column)


def create_index_if_missing(
    index_name: str,
    table: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if not index_exists(table, index_name):
        op.create_index(index_name, table, columns, unique=unique)


def drop_index_if_exists(index_name: str, table: str) -> None:
    if index_exists(table, index_name):
        op.drop_index(index_name, table_name=table)
