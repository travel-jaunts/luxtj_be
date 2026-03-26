from datetime import datetime, timezone

from fastapi import FastAPI

from common.serializerlib import HealthStatusResult


async def health_check(fastapi_app: FastAPI) -> HealthStatusResult:
    return HealthStatusResult(
        uptime_seconds=int(
            (datetime.now(timezone.utc) - _get_start_timestamp(fastapi_app)).total_seconds()
        ),
        database_connected=False,  # TODO: implement actual database connectivity check
    )


async def init_app_state(fastapi_app: FastAPI):
    fastapi_app.state.start_timestamp = datetime.now(timezone.utc)


def _get_start_timestamp(fastapi_app: FastAPI) -> datetime:
    return fastapi_app.state.start_timestamp
