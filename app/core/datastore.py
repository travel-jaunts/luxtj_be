from typing import AsyncGenerator, Any
import re

from fastapi import Request, FastAPI
from pydantic_core import to_json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import MetaData

from app.config import settings


metadata_obj = MetaData(schema="luxe")

def resolve_table_name(name: str) -> str:
    """Resolves table names to their mapped names."""
    names = re.split("(?=[A-Z])", name)  # noqa
    return "_".join([x.lower() for x in names if x])


class BaseModel(AsyncAttrs, DeclarativeBase):
    """
    Base class for SQLAlchemy models.
    This class is used to define the base for all models in the application.
    It can be extended by other model classes.
    """
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return resolve_table_name(cls.__name__)
    
    metadata = metadata_obj

    def attribute_map(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the model's attributes.
        This is useful for debugging and logging purposes.
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {to_json(self.attribute_map())}>"



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
        if hasattr(app.state, "_db_session_factory"):
            del app.state._db_session_factory
        if hasattr(app.state, "_db_engine"):
            await app.state._db_engine.dispose()
            del app.state._db_engine

    @staticmethod
    def resource_db_session(request: Request) -> AsyncSession:
        """
        Dependency to provide a database connection for each request.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            AsyncSession: An asynchronous database session.
        """
        db_session_factory: async_sessionmaker[AsyncSession] = (
            request.app.state._db_session_factory
        )
        return db_session_factory()

    @staticmethod
    async def resource_db_session_transaction(
        request: Request,
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
