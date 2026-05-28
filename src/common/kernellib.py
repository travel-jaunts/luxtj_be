from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from httpx import AsyncClient

from common.serializerlib import HealthStatusResult
from luxtj.shared_kernel.infrastructure.events import (
    InProcessEventPublisher,
    PrintInProcessEventSubscriber,
)
from luxtj.utils import timeutils


@asynccontextmanager
async def init_app_state(fastapi_app: FastAPI):
    fastapi_app.state.start_timestamp = timeutils.datetime_now()

    event_publisher = InProcessEventPublisher()
    print_subscriber = PrintInProcessEventSubscriber(event_publisher=event_publisher)

    fastapi_app.state.domain_event_publisher = event_publisher
    fastapi_app.state.domain_event_subscribers = [print_subscriber]

    await print_subscriber.start()

    try:
        async with AsyncClient() as client:
            fastapi_app.state.http_client = client
            yield
    finally:
        await print_subscriber.stop()


def get_start_timestamp(fastapi_app: FastAPI) -> datetime:
    """Helper function to retrieve the application's start timestamp.
    - Can be used in Depends
    """
    return fastapi_app.state.start_timestamp


def get_http_client(fastapi_app: FastAPI) -> AsyncClient:
    """Helper function to retrieve the application's HTTP client.
    - Can be used in Depends
    """
    return fastapi_app.state.http_client


def get_domain_event_publisher(fastapi_app: FastAPI) -> InProcessEventPublisher:
    """Helper function to retrieve the application's in-process event publisher."""
    return fastapi_app.state.domain_event_publisher


def health_check(fastapi_app: FastAPI) -> HealthStatusResult:
    return HealthStatusResult(
        uptime_seconds=int(
            (timeutils.datetime_now() - get_start_timestamp(fastapi_app)).total_seconds()
        ),
        database_connected=False,  # TODO: implement actual database connectivity check
    )
