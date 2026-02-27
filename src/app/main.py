from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.logging import configure_logging, get_logger
from app.core.config import get_settings
from app.api.v1 import router as v1_router
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.exceptions import RRCycleExceptionHandler


settings = get_settings()
configure_logging(settings.app_log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    logger.info(
        "Starting up | env=%s auth=%s",
        settings.app_exec_env,
        settings.app_auth_enabled,
    )
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
    app.add_middleware(RRCycleExceptionHandler, settings=settings)
    app.add_middleware(RequestLoggingMiddleware, settings=settings)

    # Routers
    app.include_router(v1_router)

    # Built-in status check endpoints
    @app.get("/ping", tags=["ops"])
    async def _() -> PlainTextResponse:
        return PlainTextResponse("pong")

    @app.get("/health", tags=["ops"])
    async def _() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
