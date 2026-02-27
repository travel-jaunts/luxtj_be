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

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:  # pragma: no cover
        raise NotImplementedError
