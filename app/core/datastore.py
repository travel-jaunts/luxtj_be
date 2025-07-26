
from typing import AsyncGenerator

from fastapi import Request, FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings


class DataStoreCore:

    @staticmethod
    async def init_db_resources(app: FastAPI) -> None:
        """
        Initialize the database resources in the FastAPI application state.

        Args:
            app (FastAPI): The FastAPI application instance.
        """
        app.state._db_engine = create_async_engine(
            settings.DB_DSN, echo=settings.DEBUG
        )
        app.state._db_session_factory = async_sessionmaker(
            app.state._db_engine, expire_on_commit=False
        )
    
    @staticmethod
    async def release_db_resources(app: FastAPI) -> None:
        """
        Release the database resources in the FastAPI application state.

        Args:
            app (FastAPI): The FastAPI application instance.
        """
        if hasattr(app.state, '_db_session_factory'):
            del app.state._db_session_factory
        if hasattr(app.state, '_db_engine'):
            await app.state._db_engine.dispose()
            del app.state._db_engine

    @staticmethod
    def resource_db_session(
        request: Request
    ) -> AsyncSession:
        """
        Dependency to provide a database connection for each request.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            AsyncSession: An asynchronous database session.
        """
        db_session_factory: async_sessionmaker[AsyncSession] = \
            request.app.state._db_session_factory
        return db_session_factory()

    @staticmethod
    async def resource_db_session_transaction(
        request: Request
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency to provide a database connection for each request.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            AsyncSession: An asynchronous database session.
        """
        async with DataStoreCore.resource_db_session(request) as session:
            async with session.begin():
                yield session  # This will be used in the route handlers
