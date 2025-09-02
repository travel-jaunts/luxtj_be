from typing import Optional
import uuid

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response

from emporio.core.context import request_context_var


class RequestIdInjectorMiddleware(BaseHTTPMiddleware):
    _REQUEST_ID_HEADER_KEY: str = "X-Request-ID"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        _request_id: Optional[str] = request.headers.get(
            RequestIdInjectorMiddleware._REQUEST_ID_HEADER_KEY
        )
        if not _request_id:
            _request_id = str(uuid.uuid4())

        request.state.request_id = _request_id
        request_context_var.set(
            request
        )  # Store the request ID in the context variable

        response = await call_next(request)
        response.headers[RequestIdInjectorMiddleware._REQUEST_ID_HEADER_KEY] = (
            _request_id
        )

        return response
