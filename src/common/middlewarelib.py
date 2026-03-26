from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request, Response

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
