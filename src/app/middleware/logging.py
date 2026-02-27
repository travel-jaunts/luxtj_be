import time
import uuid

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.base import BaseAppMiddleware


class RequestLoggingMiddleware(BaseAppMiddleware):
    """
    Logs incoming requests and outgoing responses.
    Controlled by settings.log_requests / settings.log_responses.
    A unique request-id is added to every response for tracing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        if self.settings.app_log_requests:
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

        if self.settings.app_log_responses:
            self.logger.info(
                "RESPONSE id=%s status=%s elapsed=%.2fms",
                request_id,
                response.status_code,
                elapsed_ms,
            )

        return response
