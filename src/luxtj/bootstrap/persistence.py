from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from luxtj.shared_kernel.infrastructure.persistence import (
    AsyncSessionFactory,
    build_async_engine,
    build_async_session_factory,
    dispose_async_engine,
)


@dataclass(frozen=True)
class DatabaseResources:
    engine: AsyncEngine
    session_factory: AsyncSessionFactory


def build_database_resources(
    database_url: str,
    *,
    echo: bool = False,
) -> DatabaseResources:
    engine = build_async_engine(database_url, echo=echo)
    return DatabaseResources(
        engine=engine,
        session_factory=build_async_session_factory(engine),
    )


@asynccontextmanager
async def database_resources(
    database_url: str,
    *,
    echo: bool = False,
) -> AsyncIterator[DatabaseResources]:
    resources = build_database_resources(database_url, echo=echo)
    try:
        yield resources
    finally:
        await dispose_async_engine(resources.engine)
