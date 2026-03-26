from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends
from httpx import AsyncClient

from common.serializerlib import ApiSuccessResponse, HealthStatusResult
from common.injectorlib import fastapi_app_handle
from common.kernellib import init_app_state, health_check
from common.middlewarelib import EnforcePostMethodOnly
from admin_api.main import customer_router


@asynccontextmanager
async def api_application_lifespan(app: FastAPI):
    print("API application startup: Initializing resources...")

    await init_app_state(app)

    async with AsyncClient() as client:
        app.state.http_client = client
        yield


def server_factory() -> FastAPI:
    api_application = FastAPI(
        title="LuxTJ Public API",
        description="API for Customer applications",
        version="0.1.0",
        lifespan=api_application_lifespan,
    )

    api_application.include_router(customer_router, prefix="/admin", tags=["admin"])
    # CAUTION: in case admin apis need to be removed, comment above line

    @api_application.post("/ping", tags=["ops"])
    async def _() -> str:
        return "pong"

    @api_application.post("/health", tags=["ops"])
    async def _(
        app_core: Annotated[FastAPI, Depends(fastapi_app_handle)],
    ) -> ApiSuccessResponse[HealthStatusResult]:
        return ApiSuccessResponse(
            output=await health_check(app_core),
        )

    api_application.add_middleware(EnforcePostMethodOnly)

    return api_application
