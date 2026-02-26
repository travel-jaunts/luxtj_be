"""
Application factory.

Middleware is registered in *reverse* order of desired execution because
Starlette wraps each layer from the outside in:
  1. RequestLoggingMiddleware  – outermost (logs first/last)
  2. KeycloakAuthMiddleware    – runs after logging, before route handlers
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.middleware import KeycloakAuthMiddleware, RequestLoggingMiddleware, RRCycleExceptionHandler

settings = get_settings()
configure_logging(settings.app_log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info(
        "Starting up | env=%s auth=%s",
        settings.app_env,
        settings.auth_enabled,
    )
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LuxTJ Backend",
        version="0.1.0",
        lifespan=app_lifespan,
        # Hide docs in production if desired
        docs_url="/docs" if settings.is_dev else None,
        redoc_url="/redoc" if settings.is_dev else None,
    )

    # ── Middleware (registered outermost → innermost) ─────────────────
    # Keycloak auth is registered first so logging wraps around it
    app.add_middleware(KeycloakAuthMiddleware, settings=settings)
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
