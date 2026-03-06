from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.logging import configure_logging, get_logger
from app.core.config import get_settings
from app.api.v1 import router as v1_router
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.exceptions import RRCycleExceptionHandler
from app.middleware.method_validator import MethodValidatorMiddleware
from app.core.response_models import SuccessResponse, RequestProcessStatus
from app.core.database import engine, Base


settings = get_settings()
configure_logging(settings.app_log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info(
        "Starting up | env=%s auth=%s",
        settings.app_exec_env,
        settings.app_auth_enabled,
    )
    async with AsyncClient() as client:
        app.state.http_client = client
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        lifespan=app_lifespan,
    )

    # ── Middleware (registered outermost → innermost) ─────────────────
    # Keycloak auth is registered first so logging wraps around it
    # app.add_middleware(KeycloakAuthMiddleware, settings=settings)
    app.add_middleware(MethodValidatorMiddleware, settings=settings)
    app.add_middleware(RRCycleExceptionHandler, settings=settings)
    app.add_middleware(RequestLoggingMiddleware, settings=settings)

    # Routers
    app.include_router(v1_router)

    # Built-in status check endpoints
    @app.post("/ping", tags=["ops"])
    async def _() -> PlainTextResponse:
        return PlainTextResponse("pong")

    @app.post("/health", tags=["ops"])
    async def _() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content=SuccessResponse(status=RequestProcessStatus.OK, output=None).model_dump(
                exclude_none=True
            ),
        )

    return app


app = create_app()
