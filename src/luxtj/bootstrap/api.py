from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import MetaData
from starlette.middleware.cors import CORSMiddleware
from twilio.http.async_http_client import AsyncTwilioHttpClient

from admin_api.audit_logs.router import audit_logs_router as admin_audit_logs_router
from admin_api.customer.router import customer_router
from admin_api.partner.router import partner_router
from admin_api.reports.router import reports_router
from luxtj.bootstrap import config
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_models import AccountAuthBase
from luxtj.contexts.account.presentation.http.router import account_auth_router
from luxtj.contexts.acquisition.infrastructure.persistence.sqlalchemy_models import AcquisitionBase
from luxtj.contexts.acquisition.presentation.http.router import router as waitlist_router
from luxtj.contexts.action_centre.infrastructure.persistence.sqlalchemy_models import (
    ActionCentreBase,
)
from luxtj.contexts.action_centre.infrastructure.projector import ActionCentreOutboxProjector
from luxtj.contexts.action_centre.presentation.http.router import action_centre_router
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import CustomerBase
from luxtj.contexts.customer.presentation.http.router import customer_bucket_list_router
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import MarketingBase
from luxtj.contexts.marketing.presentation.http.router import marketing_router
from luxtj.shared_kernel.infrastructure.events.in_process import (
    InProcessEventPublisher,
    PrintInProcessEventSubscriber,
)
from luxtj.shared_kernel.infrastructure.persistence.outbox_model import SharedKernelBase
from luxtj.shared_kernel.infrastructure.persistence.sqlalchemy import (
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
    return (
        SharedKernelBase.metadata,
        AccountAuthBase.metadata,
        MarketingBase.metadata,
        ActionCentreBase.metadata,
        AcquisitionBase.metadata,
        CustomerBase.metadata,
    )


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
        session_factory = build_async_session_factory(database_engine)
        fastapi_app.state.database_session_factory = session_factory

        if config.ENABLE_OUTBOX_PROJECTOR:
            action_centre_projector = ActionCentreOutboxProjector(session_factory)
            fastapi_app.state.action_centre_projector = action_centre_projector
            await action_centre_projector.start()

        async with AsyncClient() as client, AsyncTwilioHttpClient() as async_http_client:
            fastapi_app.state.http_client = client
            fastapi_app.state.twilio_http_client = async_http_client
            yield
    finally:
        if getattr(fastapi_app.state, "action_centre_projector", None) is not None:
            await fastapi_app.state.action_centre_projector.stop()

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
    admin_router.include_router(action_centre_router)
    admin_router.include_router(admin_audit_logs_router)
    api_application.include_router(admin_router)
    # CAUTION: in case admin apis need to be removed, comment above lines

    public_router = APIRouter(prefix="/v1")
    public_router.include_router(waitlist_router)
    public_router.include_router(account_auth_router)
    public_router.include_router(customer_bucket_list_router)
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

    if config.ENVIRONMENT == "development":
        api_application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return api_application


# uv run --env-file .dev.env uvicorn luxtj.bootstrap.api:server_factory --factory
