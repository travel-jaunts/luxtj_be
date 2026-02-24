"""
Middleware base class and request/response logging middleware.

All custom middleware should extend BaseAppMiddleware so they share
a common logger and settings reference.
"""

import time
import uuid

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import Settings, get_settings
from app.core.logging import get_logger


class BaseAppMiddleware(BaseHTTPMiddleware):
    """Shared base for all application middleware."""

    def __init__(self, app: ASGIApp, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.logger = get_logger(self.__class__.__module__)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # pragma: no cover
        raise NotImplementedError


class RequestLoggingMiddleware(BaseAppMiddleware):
    """
    Logs incoming requests and outgoing responses.
    Controlled by settings.log_requests / settings.log_responses.
    A unique request-id is added to every response for tracing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        if self.settings.log_requests:
            self.logger.info(
                "REQUEST  id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-Id"] = request_id

        if self.settings.log_responses:
            self.logger.info(
                "RESPONSE id=%s status=%s elapsed=%.2fms",
                request_id,
                response.status_code,
                elapsed_ms,
            )

        return response
