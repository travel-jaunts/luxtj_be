from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import MetaData

from admin_api.audit_logs import admin_audit_logs_router
from admin_api.customer import customer_router
from admin_api.partner import partner_router
from admin_api.reports import reports_router
from luxtj.bootstrap import config
from luxtj.contexts.marketing.infrastructure.persistence import MarketingBase
from luxtj.contexts.marketing.presentation.http import marketing_router
from luxtj.shared_kernel.infrastructure.events import (
    InProcessEventPublisher,
    PrintInProcessEventSubscriber,
)
from luxtj.shared_kernel.infrastructure.persistence import (
    SharedKernelBase,
    build_async_engine,
    build_async_session_factory,
    dispose_async_engine,
)
from luxtj.shared_kernel.presentation.http.dependencies import fastapi_app_handle
from luxtj.shared_kernel.presentation.http.middleware import (
    EndpointExceptionHandler,
    EnforcePostMethodOnly,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse, HealthStatusResult
from luxtj.utils import timeutils


def get_registered_metadata() -> tuple[MetaData, ...]:
    # Register context metadata here so startup table creation can cover all contexts.
    return (SharedKernelBase.metadata, MarketingBase.metadata)


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


async def _is_database_connected(fastapi_app: FastAPI) -> bool:
    database_engine: AsyncEngine | None = fastapi_app.state.database_engine
    if database_engine is None:
        return False
    try:
        async with database_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


async def health_check(fastapi_app: FastAPI) -> HealthStatusResult:
    start: datetime = fastapi_app.state.start_timestamp
    return HealthStatusResult(
        uptime_seconds=int((timeutils.datetime_now() - start).total_seconds()),
        database_connected=await _is_database_connected(fastapi_app),
    )


@asynccontextmanager
async def api_application_lifespan(app: FastAPI):
    print("API application startup: Initializing resources...")
    async with init_app_state(app):
        yield


def server_factory() -> FastAPI:
    api_application = FastAPI(
        title="LuxTJ Public API",
        description="API for Customer applications",
        version=config.VERSION,
        lifespan=api_application_lifespan,
    )

    admin_router = APIRouter(prefix="/v1/admin")
    admin_router.include_router(customer_router)
    admin_router.include_router(partner_router)
    admin_router.include_router(reports_router)
    admin_router.include_router(marketing_router)
    admin_router.include_router(admin_audit_logs_router)
    api_application.include_router(admin_router)
    # CAUTION: in case admin apis need to be removed, comment above lines

    public_router = APIRouter(prefix="/v1")
    # public_router.include_router(idam_router)
    api_application.include_router(public_router)

    @api_application.post("/ping", tags=["ops"])
    async def _() -> str:
        return "pong"

    @api_application.post("/health", tags=["ops"])
    async def _(
        app_core: Annotated[FastAPI, Depends(fastapi_app_handle)],
    ) -> ApiSuccessResponse[HealthStatusResult]:
        return ApiSuccessResponse(
            output=await health_check(app_core),
        )

    api_application.add_middleware(EndpointExceptionHandler)
    api_application.add_middleware(EnforcePostMethodOnly)  # outermost

    return api_application


# uv run --env-file .dev.env uvicorn luxtj.bootstrap.api:server_factory --factory
