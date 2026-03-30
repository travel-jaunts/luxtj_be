from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI
from niquests import Session

from common.serializerlib import HealthStatusResult


@asynccontextmanager
async def init_app_state(fastapi_app: FastAPI):
    fastapi_app.state.start_timestamp = datetime.now(timezone.utc)
    with Session() as client:
        fastapi_app.state.http_client = client
        yield


def get_start_timestamp(fastapi_app: FastAPI) -> datetime:
    """Helper function to retrieve the application's start timestamp.
    - Can be used in Depends
    """
    return fastapi_app.state.start_timestamp


def get_http_client(fastapi_app: FastAPI) -> Session:
    """Helper function to retrieve the application's HTTP client.
    - Can be used in Depends
    """
    return fastapi_app.state.http_client


def health_check(fastapi_app: FastAPI) -> HealthStatusResult:
    return HealthStatusResult(
        uptime_seconds=int(
            (datetime.now(timezone.utc) - get_start_timestamp(fastapi_app)).total_seconds()
        ),
        database_connected=False,  # TODO: implement actual database connectivity check
    )
