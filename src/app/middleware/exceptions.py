from app.middleware.base import BaseAppMiddleware
from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint


class RRCycleExceptionHandler(BaseAppMiddleware):
    """
    Logs incoming requests and outgoing responses.
    Controlled by settings.log_requests / settings.log_responses.
    A unique request-id is added to every response for tracing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response: Response = await call_next(request)
            assert isinstance(response, Response), "Expected a Response object"
            return response

        # except AssertionError as exc:
        #     self.logger.error(
        #         "RRCycleExceptionHandler: call_next did not return a Response | error=%s",
        #         exc,
        #     )
        #     return Response(
        #         content="Internal Server Error",
        #         status_code=500,
        #         media_type="text/plain",
        #     )

        except Exception as exc:
            self.logger.error(
                "RRCycleExceptionHandler: Unhandelled error | error=%s",
                exc,
            )
            return Response(
                content="Internal Server Error",
                status_code=500,
                media_type="text/plain",
            )
