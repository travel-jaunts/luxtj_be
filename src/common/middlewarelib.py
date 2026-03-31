from fastapi import Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from common.serializerlib import ApiErrorResponse


class EnforcePostMethodOnly(BaseHTTPMiddleware):
    """Middleware to allow only POST methods, while allowing GET access
    to documentation and OpenAPI schema.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response | JSONResponse:
        if (
            "/docs" in request.url.path
            or "/redoc" in request.url.path
            or "/openapi.json" in request.url.path
        ):
            return await call_next(request)
        if request.method != "POST":
            return JSONResponse(
                status_code=400,
                content=ApiErrorResponse(error_message="unsupported method").model_dump(
                    by_alias=True
                ),
            )
        return await call_next(request)


class EndpointExceptionHandler(BaseHTTPMiddleware):
    """Middleware to catch unhandled exceptions in endpoints and return a JSON response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response | JSONResponse:

        span = trace.get_current_span()
        if span and span.is_recording():
            trace_id = span.get_span_context().trace_id
        else:
            trace_id = 0

        try:
            return await call_next(request)

        except Exception:
            # Log the exception here if needed
            return JSONResponse(
                status_code=200,
                content=ApiErrorResponse(
                    error_message=f"internal server error, please file a report with request id {trace_id:032x}"
                ).model_dump(by_alias=True),
            )
