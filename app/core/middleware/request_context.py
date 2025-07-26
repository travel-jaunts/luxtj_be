from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import RequestContext
from app.core.datastore import DataStoreCore


class ApplicationRequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        async with DataStoreCore.resource_db_session(request) as db_session:
            async with db_session.begin():
                request.state.db_session = db_session
                RequestContext.set_request(
                    request
                )  # Store the request in the context variable
                response = await call_next(request)

        return response
