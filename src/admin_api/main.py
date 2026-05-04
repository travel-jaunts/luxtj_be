from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from admin_api.audit_logs import admin_audit_logs_router
from admin_api.customer import customer_router
from admin_api.reports import reports_router
from common.injectorlib import fastapi_app_handle
from common.kernellib import health_check, init_app_state
from common.serializerlib import ApiSuccessResponse, HealthStatusResult


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
    api_application.include_router(reports_router)
    api_application.include_router(admin_audit_logs_router)

    @api_application.post("/ping", tags=["ops"])
    def _() -> str:
        return "pong"

    @api_application.post("/health", tags=["ops"])
    def _(
        app_core: Annotated[FastAPI, Depends(fastapi_app_handle)],
    ) -> ApiSuccessResponse[HealthStatusResult]:
        return ApiSuccessResponse(
            output=health_check(app_core),
        )

    return api_application
