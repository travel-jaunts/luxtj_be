from fastapi import APIRouter

from .serializer import BaseSerializer


class HealthCheckResponse(BaseSerializer):
    """
    Serializer for the health check response.
    This class defines the structure of the response returned by the health check endpoint.
    """

    status: str = "healthy"


v1_router = APIRouter(
    prefix="/v1",
    tags=["v1"],
)


@v1_router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint to verify the service is running.

    Returns:
        dict: A dictionary indicating the service is healthy.
    """
    return HealthCheckResponse()
