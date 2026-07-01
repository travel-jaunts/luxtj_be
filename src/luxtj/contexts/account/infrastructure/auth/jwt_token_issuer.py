from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import jwt

from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class JoseJwtTokenIssuer:
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
        self, *, account_id: UUID, phone_identity: PhoneIdentity
    ) -> tuple[str, str]:
        now = datetime.now(tz=UTC)
        access_token = jwt.encode(
            {
                "sub": str(account_id),
                "dial_code": phone_identity.dial_code,
                "phone_number": phone_identity.phone_number,
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(seconds=self._access_ttl_seconds)).timestamp()),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        refresh_token = jwt.encode(
            {
                "sub": str(account_id),
                "type": "refresh",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(seconds=self._refresh_ttl_seconds)).timestamp()),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        return access_token, refresh_token
