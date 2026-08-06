from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from jose import JWTError

from luxtj.bootstrap import config
from luxtj.contexts.identity.domain.enums import UserTypeEnum
from luxtj.contexts.identity.infrastructure.auth.jwt import JoseIdentityTokenIssuer


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: UUID
    email: str
    user_type: UserTypeEnum
    role_id: UUID | None
    permissions: frozenset[str]
    name: str | None = None

    @property
    def is_superadmin(self) -> bool:
        return self.user_type == UserTypeEnum.SUPERADMIN

    def has_permission(self, code: str) -> bool:
        if self.is_superadmin or "*" in self.permissions:
            return True
        return code in self.permissions


def _token_issuer() -> JoseIdentityTokenIssuer:
    return JoseIdentityTokenIssuer(
        secret=config.AUTH_JWT_SECRET,
        algorithm=config.AUTH_JWT_ALGORITHM,
        access_ttl_seconds=config.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds=config.AUTH_REFRESH_TOKEN_TTL_SECONDS,
    )


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1].strip()


async def get_current_principal(request: Request) -> AuthenticatedPrincipal:
    """Authentication middleware: validates Bearer JWT and returns principal."""
    raw = _extract_bearer_token(request)
    issuer = _token_issuer()
    try:
        payload = issuer.decode_access_token(raw)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")

    try:
        user_type = UserTypeEnum(str(payload.get("user_type")))
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token claims") from exc

    role_raw = payload.get("role_id")
    role_id = UUID(str(role_raw)) if role_raw else None
    permissions_raw = payload.get("permissions") or []
    if not isinstance(permissions_raw, list):
        permissions_raw = []

    return AuthenticatedPrincipal(
        user_id=user_id,
        email=str(payload.get("email") or ""),
        user_type=user_type,
        role_id=role_id,
        permissions=frozenset(str(item) for item in permissions_raw),
        name=str(payload.get("name")) if payload.get("name") else None,
    )


def require_user_types(*allowed: UserTypeEnum):
    """Authentication middleware: restrict by user type."""

    async def _dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if principal.user_type not in allowed:
            raise HTTPException(status_code=403, detail="User type is not allowed")
        return principal

    return _dependency


def require_permission(permission_code: str):
    """Authorization middleware: admin routes must have permission (superadmin bypass)."""

    async def _dependency(
        principal: AuthenticatedPrincipal = Depends(
            require_user_types(UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN)
        ),
    ) -> AuthenticatedPrincipal:
        if not principal.has_permission(permission_code):
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: {permission_code}",
            )
        return principal

    return _dependency


RequireAdminPortal = require_user_types(UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN)
