from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.base import BaseAppMiddleware, RequestResponseEndpoint
from app.core.response_models import ErrorResponse, RequestProcessStatus



class MethodValidatorMiddleware(BaseAppMiddleware):
    """Middleware to allow only POST methods."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if "/docs" in request.url.path or "/redoc" in request.url.path or "/openapi.json" in request.url.path:
            return await call_next(request)
        if request.method != "POST":
            return JSONResponse(
                status_code=200,
                content=ErrorResponse(
                    status=RequestProcessStatus.ERROR,
                    errorMessage="unsupported method"
                ).model_dump()
            )
        return await call_next(request)
