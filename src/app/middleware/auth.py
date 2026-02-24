"""
Keycloak OAuth 2.0 / OIDC authorization middleware.

When AUTH_ENABLED=true the middleware validates the Bearer token present in
every request against Keycloak's userinfo endpoint.  The decoded claims are
attached to request.state.user so downstream handlers can inspect them.

Set AUTH_ENABLED=false (the default for APP_ENV=development) to bypass auth
entirely - handy for local development without a running Keycloak instance.

Extending:
    Create a subclass of KeycloakAuthMiddleware and override
    `_is_path_excluded` to whitelist additional paths, or override
    `_extract_token` to support non-standard header schemes.
"""

from typing import Any

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp
from starlette.middleware.base import RequestResponseEndpoint


from app.core.config import Settings
from app.middleware.base import BaseAppMiddleware

# Paths that never require authentication
_DEFAULT_EXCLUDED_PATHS: frozenset[str] = frozenset(
    {"/health", "/docs", "/openapi.json", "/redoc"}
)


class KeycloakAuthMiddleware(BaseAppMiddleware):
    """Validate Bearer tokens via Keycloak's userinfo endpoint."""

    def __init__(
        self,
        app: ASGIApp,
        settings: Settings | None = None,
        excluded_paths: frozenset[str] | None = None,
    ) -> None:
        super().__init__(app, settings)
        self._excluded = excluded_paths or _DEFAULT_EXCLUDED_PATHS

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _is_path_excluded(self, path: str) -> bool:
        """Return True for paths that should skip auth checks."""
        return path in self._excluded

    def _extract_token(self, request: Request) -> str | None:
        """Pull the Bearer token from the Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[len("Bearer "):]
        return None

    # ------------------------------------------------------------------
    # Middleware dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.settings.auth_enabled:
            self.logger.debug("Auth disabled – skipping token validation")
            return await call_next(request)

        if self._is_path_excluded(request.url.path):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        claims = await self._validate_token(token)
        if claims is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token validation failed"},
            )

        request.state.user = claims
        self.logger.debug("Authenticated user sub=%s", claims.get("sub"))
        return await call_next(request)

    async def _validate_token(self, token: str) -> Any | None:
        """
        Call Keycloak's userinfo endpoint to validate the access token.
        Returns the claims dict on success, None on failure.

        Swap this implementation for JWT introspection / JWKS verification
        if you prefer local validation without a round-trip to Keycloak.
        """
        url = self.settings.keycloak_userinfo_endpoint
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    url, headers={"Authorization": f"Bearer {token}"}
                )
            if resp.status_code == 200:
                return resp.json()
            self.logger.warning(
                "Keycloak returned %s for userinfo request", resp.status_code
            )
        except httpx.RequestError as exc:
            self.logger.error("Could not reach Keycloak: %s", exc)
        return None
