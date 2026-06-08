import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Allow imports from src/ when running alembic from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import (
    MarketingBase,
)
from luxtj.shared_kernel.infrastructure.persistence.outbox_model import (
    SharedKernelBase,
)
from luxtj.contexts.acquisition.infrastructure.persistence.sqlalchemy_models import (
    AcquisitionBase,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [SharedKernelBase.metadata, MarketingBase.metadata, AcquisitionBase.metadata]


def _get_url() -> str:
    return os.environ["LTJBE_DATABASE_URL"]


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
