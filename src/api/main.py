from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI

# from opentelemetry import trace
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
from admin_api.audit_logs import admin_audit_logs_router
from admin_api.customer import customer_router
from admin_api.partner import partner_router
from api import config
from common.injectorlib import fastapi_app_handle
from common.kernellib import health_check, init_app_state
from common.middlewarelib import EndpointExceptionHandler, EnforcePostMethodOnly
from common.serializerlib import ApiSuccessResponse, HealthStatusResult


@asynccontextmanager
async def api_application_lifespan(app: FastAPI):
    print("API application startup: Initializing resources...")

    async with init_app_state(app):
        yield


def server_factory() -> FastAPI:
    api_application = FastAPI(
        title="LuxTJ Public API",
        description="API for Customer applications",
        version=config.VERSION,
        lifespan=api_application_lifespan,
    )

    admin_router = APIRouter(prefix="/v1/admin")
    admin_router.include_router(customer_router)
    admin_router.include_router(partner_router)
    admin_router.include_router(admin_audit_logs_router)
    api_application.include_router(admin_router)
    # CAUTION: in case admin apis need to be removed, comment above lines

    @api_application.post("/ping", tags=["ops"])
    async def _() -> str:
        return "pong"

    @api_application.post("/health", tags=["ops"])
    async def _(
        app_core: Annotated[FastAPI, Depends(fastapi_app_handle)],
    ) -> ApiSuccessResponse[HealthStatusResult]:
        return ApiSuccessResponse(
            output=health_check(app_core),
        )

    api_application.add_middleware(EndpointExceptionHandler)
    api_application.add_middleware(EnforcePostMethodOnly)  # outermost

    # init tracing --------------------------------------------------------------------------------
    # span_processor = BatchSpanProcessor(
    #     OTLPSpanExporter(endpoint=config.OTEL_ENDPOINT, insecure=True)
    # )
    # api_trace_provider = TracerProvider(
    #     resource=Resource.create(
    #         attributes={
    #             "service.name": config.OTEL_SERVICE_NAME,
    #             "service.version": config.VERSION,
    #             "deployment.environment": config.ENVIRONMENT,
    #         }
    #     ),
    # )
    # api_trace_provider.add_span_processor(span_processor)
    # trace.set_tracer_provider(api_trace_provider)

    # if config.OTEL_ENDPOINT:
    #     FastAPIInstrumentor.instrument_app(
    #         api_application,
    #         tracer_provider=api_trace_provider,
    #     )

    return api_application


# uv run --env-file .dev.env uvicorn api.main:server_factory --factory
