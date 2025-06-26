from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.router import v1_router
from app.config import settings


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
    app.state._db_engine = create_async_engine(settings.DB_DSN, echo=settings.DEBUG)
    app.state._db_session = async_sessionmaker(
        app.state._db_engine, expire_on_commit=False
    )
    
    yield  # Startup tasks can be added here
    
    # Shutdown tasks can be added here if needed
    await app.state._db_engine.dispose()


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
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    return app
