from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends

from common.serializerlib import ApiSuccessResponse, HealthStatusResult
from common.injectorlib import fastapi_app_handle
from common.kernellib import init_app_state, health_check
from admin_api.customer import customer_router


@asynccontextmanager
async def admin_api_application_lifespan(app: FastAPI):
    print("Admin API application startup: Initializing resources...")

    async with init_app_state(app):
        yield


def server_factory() -> FastAPI:
    api_application = FastAPI(
        title="LuxTJ Admin API",
        description="API for Admin Dashboard",
        version="0.1.0",
        lifespan=admin_api_application_lifespan,
    )

    api_application.include_router(customer_router)

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

    return api_application
