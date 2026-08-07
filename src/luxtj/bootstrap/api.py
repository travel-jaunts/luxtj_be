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
from luxtj.contexts.action_centre.presentation.http.router import action_centre_router
from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import CrsBase
from luxtj.contexts.crs.presentation.http.inventory_router import crs_inventory_router
from luxtj.contexts.crs.presentation.http.mapping_router import crs_mapping_router
from luxtj.contexts.currency.application.use_cases import CurrencyActivationService
from luxtj.contexts.currency.bootstrap import init_currency_conversion
from luxtj.contexts.currency.infrastructure.active_currencies_cache import (
    get_active_currencies_cache,
)
from luxtj.contexts.currency.infrastructure.currency_conversion import get_currency_conversion
from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_models import CurrencyBase
from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyActiveCurrencyRepository,
)
from luxtj.contexts.currency.presentation.http.router import (
    admin_currencies_router,
    public_currencies_router,
)
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import CustomerBase
from luxtj.contexts.customer.presentation.http.router import (
    customer_bucket_list_router,
    customer_personal_calendar_router,
)
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import HotelBase
from luxtj.contexts.hotel.presentation.http.hotel_router import hotel_router
from luxtj.contexts.hotel.presentation.http.markup_router import hotel_markup_router
from luxtj.contexts.identity.bootstrap import build_identity_bootstrap_service
from luxtj.contexts.identity.infrastructure.persistence.sqlalchemy_models import IdentityBase
from luxtj.contexts.identity.presentation.http.router import (
    admin_identity_router,
    public_auth_router,
)
from luxtj.contexts.integration.application.use_cases import IntegrationRegistryService
from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_models import IntegrationBase
from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyIntegrationRepository,
)
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.contexts.integration.presentation.http.router import integrations_router
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import MarketingBase
from luxtj.contexts.marketing.presentation.http.router import marketing_router
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_models import PaymentBase
from luxtj.contexts.payment.presentation.http.router import payment_gateway_router
from luxtj.shared_kernel.infrastructure.events.in_process import (
    InProcessEventPublisher,
    PrintInProcessEventSubscriber,
)
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle
from luxtj.shared_kernel.infrastructure.persistence.outbox_model import SharedKernelBase
from luxtj.shared_kernel.infrastructure.persistence.sqlalchemy import (
    build_async_engine,
    build_async_session_factory,
    dispose_async_engine,
    session_scope,
)
from luxtj.shared_kernel.presentation.http.dependencies import fastapi_app_handle
from luxtj.shared_kernel.presentation.http.middleware import (
    EndpointExceptionHandler,
    EnforcePostMethodOnly,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse, HealthStatusResult
from luxtj.utils import timeutils

logger = get_logger_handle(__name__)


def get_registered_metadata() -> tuple[MetaData, ...]:
    return (
        SharedKernelBase.metadata,
        AccountAuthBase.metadata,
        MarketingBase.metadata,
        ActionCentreBase.metadata,
        AcquisitionBase.metadata,
        CustomerBase.metadata,
        IdentityBase.metadata,
        IntegrationBase.metadata,
        CurrencyBase.metadata,
        HotelBase.metadata,
        PaymentBase.metadata,
    )


def get_crs_metadata() -> tuple[MetaData, ...]:
    return (CrsBase.metadata,)


def _create_all_tables(connection: Connection) -> None:
    for metadata in get_registered_metadata():
        metadata.create_all(bind=connection)


def _create_crs_tables(connection: Connection) -> None:
    for metadata in get_crs_metadata():
        metadata.create_all(bind=connection)


async def create_required_tables(database_engine: AsyncEngine) -> None:
    async with database_engine.begin() as connection:
        await connection.run_sync(_create_all_tables)


async def create_crs_tables(crs_engine: AsyncEngine) -> None:
    async with crs_engine.begin() as connection:
        await connection.run_sync(_create_crs_tables)


async def seed_identity(session_factory) -> None:
    async with session_scope(session_factory) as session:
        bootstrap = build_identity_bootstrap_service(session)
        await bootstrap.seed_permissions()
        await bootstrap.ensure_superadmin(
            email=config.SUPERADMIN_EMAIL,
            password=config.SUPERADMIN_PASSWORD,
            full_name=config.SUPERADMIN_FULL_NAME,
        )


async def seed_integrations(session_factory) -> None:
    async with session_scope(session_factory) as session:
        service = IntegrationRegistryService(
            repository=SqlAlchemyIntegrationRepository(session),
            cache=get_integration_registry(),
        )
        await service.sync_catalog()


async def seed_currencies(session_factory) -> None:
    init_currency_conversion()
    async with session_scope(session_factory) as session:
        service = CurrencyActivationService(
            repository=SqlAlchemyActiveCurrencyRepository(session),
            cache=get_active_currencies_cache(),
            conversion=get_currency_conversion(),
        )
        await service.bootstrap()
        get_currency_conversion().refresh_all_rates()


@asynccontextmanager
async def init_app_state(fastapi_app: FastAPI):
    fastapi_app.state.start_timestamp = timeutils.datetime_now()
    fastapi_app.state.database_engine = None
    fastapi_app.state.database_session_factory = None
    fastapi_app.state.crs_database_engine = None
    fastapi_app.state.crs_database_session_factory = None

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

        same_crs_url = config.CRS_DATABASE_URL == config.DATABASE_URL
        if same_crs_url:
            crs_engine = database_engine
            crs_session_factory = session_factory
        else:
            crs_engine = build_async_engine(
                config.CRS_DATABASE_URL,
                echo=config.DATABASE_ECHO,
            )
            crs_session_factory = build_async_session_factory(crs_engine)
        fastapi_app.state.crs_database_engine = crs_engine
        fastapi_app.state.crs_database_session_factory = crs_session_factory
        if config.DATABASE_AUTO_CREATE:
            await create_crs_tables(crs_engine)

        await seed_identity(session_factory)
        await seed_integrations(session_factory)
        await seed_currencies(session_factory)

        async with AsyncClient() as client, AsyncTwilioHttpClient() as async_http_client:
            fastapi_app.state.http_client = client
            fastapi_app.state.twilio_http_client = async_http_client
            yield
    finally:
        await print_subscriber.stop()
        crs_engine = fastapi_app.state.crs_database_engine
        main_engine = fastapi_app.state.database_engine
        if crs_engine is not None and crs_engine is not main_engine:
            await dispose_async_engine(crs_engine)
        await dispose_async_engine(main_engine)


async def _is_database_connected(fastapi_app: FastAPI) -> bool:
    database_engine: AsyncEngine | None = fastapi_app.state.database_engine
    if database_engine is None:
        return False
    try:
        async with database_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    crs_engine: AsyncEngine | None = getattr(fastapi_app.state, "crs_database_engine", None)
    if crs_engine is not None and crs_engine is not database_engine:
        try:
            async with crs_engine.connect() as connection:
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
    logger.info("API application startup: Initializing resources...")
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
    admin_router.include_router(admin_identity_router)
    admin_router.include_router(integrations_router)
    admin_router.include_router(admin_currencies_router)
    admin_router.include_router(customer_router)
    admin_router.include_router(partner_router)
    admin_router.include_router(reports_router)
    admin_router.include_router(marketing_router)
    admin_router.include_router(action_centre_router)
    admin_router.include_router(admin_audit_logs_router)
    admin_router.include_router(crs_mapping_router)
    admin_router.include_router(crs_inventory_router)
    admin_router.include_router(hotel_markup_router)
    api_application.include_router(admin_router)

    public_router = APIRouter(prefix="/v1")
    public_router.include_router(public_auth_router)
    public_router.include_router(waitlist_router)
    public_router.include_router(account_auth_router)
    public_router.include_router(customer_bucket_list_router)
    public_router.include_router(customer_personal_calendar_router)
    public_router.include_router(public_currencies_router)
    public_router.include_router(payment_gateway_router)
    public_router.include_router(hotel_router)
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
    api_application.add_middleware(EnforcePostMethodOnly)

    if config.ENVIRONMENT == "development":
        api_application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return api_application
