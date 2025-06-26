
from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def resource_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to provide a database connection for each request.

    Args:
        request (Request): The FastAPI request object.

    Returns:
        AsyncSession: An asynchronous database session.
    """
    db_session_factory: async_sessionmaker[AsyncSession] = request.app.state._db_session
    async with db_session_factory() as session:
        yield session  # This will be used in the route handlers
