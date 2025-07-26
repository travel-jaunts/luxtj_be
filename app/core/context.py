import contextvars

from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidConfigurationException

request_context_var: contextvars.ContextVar[Request] = contextvars.ContextVar(
    "context_request"
)


class RequestContext:
    @staticmethod
    def set_request(request: Request) -> contextvars.Token[Request]:
        """
        Set the request in the context variable.

        Args:
            request (Request): The FastAPI request object.
        """
        return request_context_var.set(request)

    @staticmethod
    def get_db_session() -> AsyncSession:
        """
        Get the database session from the context variable.

        Returns:
            AsyncSession: The database session if set, otherwise None.
        """
        request = request_context_var.get()
        if request and hasattr(request.state, "db_session"):
            if isinstance(request.state.db_session, AsyncSession):
                return request.state.db_session
        raise InvalidConfigurationException(
            "No database session found in the request context."
        )
