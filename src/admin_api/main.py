from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from admin_api.audit_logs import admin_audit_logs_router
from admin_api.customer import customer_router
from admin_api.reports import reports_router
from luxtj.bootstrap.api import health_check, init_app_state
from luxtj.contexts.marketing.presentation.http import marketing_router
from luxtj.shared_kernel.presentation.http.dependencies import fastapi_app_handle
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse, HealthStatusResult


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
    api_application.include_router(marketing_router)
    api_application.include_router(reports_router)
    api_application.include_router(admin_audit_logs_router)

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
