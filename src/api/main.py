from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, APIRouter, Depends
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

from common.serializerlib import ApiSuccessResponse, HealthStatusResult
from common.injectorlib import fastapi_app_handle
from common.kernellib import init_app_state, health_check
from common.middlewarelib import EnforcePostMethodOnly
from common.telemetry.niquests import NiquestsInstrumentor

from api import config
from admin_api.main import customer_router


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

    admin_router = APIRouter(prefix="/admin", tags=["admin"])
    admin_router.include_router(customer_router)
    api_application.include_router(admin_router)
    # CAUTION: in case admin apis need to be removed, comment above lines

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

    api_application.add_middleware(EnforcePostMethodOnly)  # outermost

    # init tracing --------------------------------------------------------------------------------
    span_processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=config.OTEL_ENDPOINT, insecure=True)
    )
    api_trace_provider = TracerProvider(
        resource=Resource.create(
            attributes={
                "service.name": config.OTEL_SERVICE_NAME,
                "service.version": config.VERSION,
                "deployment.environment": config.ENVIRONMENT,
            }
        ),
    )
    api_trace_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(api_trace_provider)

    NiquestsInstrumentor().instrument(tracer_provider=api_trace_provider)
    FastAPIInstrumentor.instrument_app(
        api_application,
        tracer_provider=api_trace_provider,
    )

    return api_application


# uv run --env-file .dev.env uvicorn api.main:server_factory --factory
