from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from emporio.core.serializer import BaseSerializer
from emporio.user.router import user_router
from emporio.personal_travel_calendar.router import personal_travel_calendar
from emporio.core.context import RequestContext
from emporio.config.logger import LOGGER


class DatabaseHealthResponse(BaseSerializer):
    """
    Serializer for the database health response.
    This class defines the structure of the database health check response.
    """

    is_connected: bool


class HealthCheckResponse(BaseSerializer):
    """
    Serializer for the health check response.
    This class defines the structure of the response returned by the health check endpoint.
    """

    status: str = "healthy"
    database: DatabaseHealthResponse


v1_router = APIRouter(
    prefix="/v1",
    tags=["v1"],
)
v1_router.include_router(user_router, prefix="/user", tags=["user"])
v1_router.include_router(
    personal_travel_calendar,
    prefix="/personal-travel-calendar",
    tags=["calendar"],
)


@v1_router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    db_session: AsyncSession = Depends(RequestContext.get_db_session),
):
    """
    Health check endpoint to verify the service is running.

    Returns:
        dict: A dictionary indicating the service is healthy.
    """
    _is_connected: bool = False
    try:
        result = await db_session.execute(
            text("SELECT 1")
        )  # Simple query to check DB connectivity
        LOGGER.info(f"Health Check DB Result: {result.scalar()}")
        _is_connected = True

    except SQLAlchemyError as persistence_exception:
        LOGGER.error(persistence_exception, exc_info=True)

    return HealthCheckResponse(
        status="healthy",
        database=DatabaseHealthResponse(is_connected=_is_connected),
    )
