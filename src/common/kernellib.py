from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import MetaData

from api import config
from common.serializerlib import HealthStatusResult
from luxtj.contexts.marketing.infrastructure.persistence import MarketingBase
from luxtj.shared_kernel.infrastructure.events import (
    InProcessEventPublisher,
    PrintInProcessEventSubscriber,
)
from luxtj.shared_kernel.infrastructure.persistence import (
    AsyncSessionFactory,
    build_async_engine,
    build_async_session_factory,
    dispose_async_engine,
)
from luxtj.utils import timeutils


def get_registered_metadata() -> tuple[MetaData, ...]:
    # Register context metadata here so startup table creation can cover all contexts.
    return (MarketingBase.metadata,)


def _create_all_tables(connection: Connection) -> None:
    for metadata in get_registered_metadata():
        metadata.create_all(bind=connection)


async def create_required_tables(database_engine: AsyncEngine) -> None:
    async with database_engine.begin() as connection:
        await connection.run_sync(_create_all_tables)


@asynccontextmanager
async def init_app_state(fastapi_app: FastAPI):
    fastapi_app.state.start_timestamp = timeutils.datetime_now()
    fastapi_app.state.database_engine = None
    fastapi_app.state.database_session_factory = None

    event_publisher = InProcessEventPublisher()
    print_subscriber = PrintInProcessEventSubscriber(event_publisher=event_publisher)

    fastapi_app.state.domain_event_publisher = event_publisher
    fastapi_app.state.domain_event_subscribers = [print_subscriber]

    await print_subscriber.start()

    try:
        database_engine = build_async_engine(
            config.DATABASE_URL,
            echo=config.DATABASE_ECHO,
        )
        fastapi_app.state.database_engine = database_engine
        if config.DATABASE_AUTO_CREATE:
            await create_required_tables(database_engine)
        fastapi_app.state.database_session_factory = build_async_session_factory(
            database_engine,
        )

        async with AsyncClient() as client:
            fastapi_app.state.http_client = client
            yield
    finally:
        await print_subscriber.stop()
        await dispose_async_engine(fastapi_app.state.database_engine)


def get_start_timestamp(fastapi_app: FastAPI) -> datetime:
    """Helper function to retrieve the application's start timestamp.
    - Can be used in Depends
    """
    return fastapi_app.state.start_timestamp


def get_http_client(fastapi_app: FastAPI) -> AsyncClient:
    """Helper function to retrieve the application's HTTP client.
    - Can be used in Depends
    """
    return fastapi_app.state.http_client


def get_domain_event_publisher(fastapi_app: FastAPI) -> InProcessEventPublisher:
    """Helper function to retrieve the application's in-process event publisher."""
    return fastapi_app.state.domain_event_publisher


def get_database_engine(fastapi_app: FastAPI) -> AsyncEngine | None:
    return fastapi_app.state.database_engine


def get_database_session_factory(fastapi_app: FastAPI) -> AsyncSessionFactory:
    return fastapi_app.state.database_session_factory


async def is_database_connected(fastapi_app: FastAPI) -> bool:
    database_engine = get_database_engine(fastapi_app)
    if database_engine is None:
        return False

    try:
        async with database_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False

    return True


async def health_check(fastapi_app: FastAPI) -> HealthStatusResult:
    return HealthStatusResult(
        uptime_seconds=int(
            (timeutils.datetime_now() - get_start_timestamp(fastapi_app)).total_seconds()
        ),
        database_connected=await is_database_connected(fastapi_app),
    )
