from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.router import v1_router
from app.config import settings
from app.core.middleware.request_context import (
    ApplicationRequestContextMiddleware,
)
from app.core.datastore import DataStoreCore


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event handler for the FastAPI application.

    This function is called when the application starts and stops.
    It can be used to perform startup and shutdown tasks.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: This function does not yield any values.
    """
    await DataStoreCore.init_db_resources(app)

    yield  # Startup tasks can be added here

    # Shutdown tasks can be added here if needed
    await DataStoreCore.release_db_resources(app)


def application_factory() -> FastAPI:
    """
    Factory function to create a FastAPI application instance.

    Returns:
        FastAPI: An instance of the FastAPI application.
    """
    app = FastAPI(
        title="luxtj backend",
        description="stateless backend process for luxtj",
        version="0.0.1alpha",
        lifespan=application_lifespan,
        debug=settings.DEBUG,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ApplicationRequestContextMiddleware)

    app.include_router(v1_router)

    return app
