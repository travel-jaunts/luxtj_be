from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.bootstrap import config
from luxtj.contexts.account.infrastructure.auth.jwt_token_issuer import JoseJwtTokenIssuer
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyAccountRepository,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle


@dataclass(frozen=True)
class AccountPrincipal:
    account_id: UUID
    dial_code: str
    phone_number: str


def _token_issuer() -> JoseJwtTokenIssuer:
    return JoseJwtTokenIssuer(
        keys=config.AUTH_ACCOUNT_JWT_KEYS,
        active_kid=config.AUTH_ACCOUNT_JWT_ACTIVE_KID,
        algorithms=config.AUTH_JWT_ALLOWED_ALGORITHMS,
        issuer=config.AUTH_ACCOUNT_JWT_ISSUER,
        audience=config.AUTH_ACCOUNT_JWT_AUDIENCE,
        clock_skew_seconds=config.AUTH_JWT_CLOCK_SKEW_SECONDS,
        access_ttl_seconds=config.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds=config.AUTH_REFRESH_TOKEN_TTL_SECONDS,
    )


def extract_bearer_token(
    value: Annotated[str | None, Depends(APIKeyHeader(name="authorization"))],
) -> str:
    if not value:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = value.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1].strip()


async def get_current_account_principal(
    raw: Annotated[str, Depends(extract_bearer_token)],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AccountPrincipal:
    try:
        payload = _token_issuer().decode_access_token(raw)
        account_id = UUID(str(payload.get("sub")))
        dial_code = str(payload["dial_code"])
        phone_number = str(payload["phone_number"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired account token") from exc

    account = await SqlAlchemyAccountRepository(session).get_by_id(account_id)
    if account is None or account.status.value != "ACTIVE":
        raise HTTPException(status_code=401, detail="Invalid or expired account token")

    return AccountPrincipal(
        account_id=account_id,
        dial_code=dial_code,
        phone_number=phone_number,
    )


async def require_account_owner(
    account_id: UUID,
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
) -> AccountPrincipal:
    if principal.account_id != account_id:
        raise HTTPException(status_code=403, detail="Account does not own this resource")
    return principal
