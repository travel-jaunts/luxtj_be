from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import jwt

from luxtj.contexts.identity.application.ports import IdentityTokenIssuer
from luxtj.contexts.identity.domain.enums import UserTypeEnum
from luxtj.contexts.identity.domain.user import User


class JoseIdentityTokenIssuer(IdentityTokenIssuer):
    def __init__(
        self,
        *,
        secret: str,
        algorithm: str,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl_seconds = access_ttl_seconds
        self._refresh_ttl_seconds = refresh_ttl_seconds

    async def issue_pair(
        self,
        *,
        user: User,
        permission_codes: list[str],
    ) -> tuple[str, str, int, int]:
        now = datetime.now(tz=UTC)
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.full_name,
            "preferred_username": user.email,
            "user_type": user.user_type.value,
            "role_id": str(user.role_id) if user.role_id else None,
            "permissions": (
                ["*"]
                if user.user_type == UserTypeEnum.SUPERADMIN
                else permission_codes
            ),
            "aud": "luxtj",
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._access_ttl_seconds)).timestamp()),
        }
        refresh_payload = {
            "sub": str(user.id),
            "user_type": user.user_type.value,
            "aud": "luxtj",
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._refresh_ttl_seconds)).timestamp()),
        }
        access_token = jwt.encode(access_payload, self._secret, algorithm=self._algorithm)
        refresh_token = jwt.encode(refresh_payload, self._secret, algorithm=self._algorithm)
        return (
            access_token,
            refresh_token,
            self._access_ttl_seconds,
            self._refresh_ttl_seconds,
        )

    def decode_access_token(self, token: str) -> dict:
        return jwt.decode(
            token,
            self._secret,
            algorithms=[self._algorithm],
            audience="luxtj",
        )
