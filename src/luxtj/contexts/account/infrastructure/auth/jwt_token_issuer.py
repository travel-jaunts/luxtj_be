from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt

from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class JoseJwtTokenIssuer:
    def __init__(
        self,
        *,
        keys: dict[str, str],
        active_kid: str,
        algorithms: tuple[str, ...],
        issuer: str,
        audience: str,
        clock_skew_seconds: int,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ) -> None:
        self._keys = keys
        self._active_kid = active_kid
        self._algorithms = algorithms
        self._issuer = issuer
        self._audience = audience
        self._clock_skew_seconds = clock_skew_seconds
        self._access_ttl_seconds = access_ttl_seconds
        self._refresh_ttl_seconds = refresh_ttl_seconds

    async def issue_pair(
        self, *, account_id: UUID, phone_identity: PhoneIdentity
    ) -> tuple[str, str]:
        now = datetime.now(tz=UTC)
        access_payload: dict[str, Any] = {
            "sub": str(account_id),
            "dial_code": phone_identity.dial_code,
            "phone_number": phone_identity.phone_number,
            "aud": self._audience,
            "iss": self._issuer,
            "type": "access",
            "jti": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._access_ttl_seconds)).timestamp()),
        }
        refresh_payload: dict[str, Any] = {
            "sub": str(account_id),
            "aud": self._audience,
            "iss": self._issuer,
            "type": "refresh",
            "jti": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._refresh_ttl_seconds)).timestamp()),
        }
        secret = self._keys[self._active_kid]
        access_token = jwt.encode(
            access_payload,
            secret,
            algorithm=self._algorithms[0],
            headers={"kid": self._active_kid},
        )
        refresh_token = jwt.encode(
            refresh_payload,
            secret,
            algorithm=self._algorithms[0],
            headers={"kid": self._active_kid},
        )
        return access_token, refresh_token

    def decode_access_token(self, token: str) -> dict[str, Any]:
        return self._decode(token, expected_type="access")

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        return self._decode(token, expected_type="refresh")

    def _decode(self, token: str, *, expected_type: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            algorithm = header.get("alg")
            if not isinstance(kid, str) or kid not in self._keys:
                raise JWTError("Unknown JWT key ID")
            if algorithm not in self._algorithms:
                raise JWTError("JWT algorithm is not allowed")
            payload = jwt.decode(
                token,
                self._keys[kid],
                algorithms=list(self._algorithms),
                audience=self._audience,
                issuer=self._issuer,
                options={"leeway": self._clock_skew_seconds},
            )
        except (JWTError, TypeError, ValueError) as exc:
            raise JWTError("Invalid account token") from exc

        if payload.get("type") != expected_type:
            raise JWTError("Unexpected account token type")
        if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("jti"), str):
            raise JWTError("Invalid account token subject or token ID")
        if not isinstance(payload.get("iat"), int) or not isinstance(payload.get("exp"), int):
            raise JWTError("Invalid account token timestamps")
        if payload["iat"] > int(datetime.now(tz=UTC).timestamp()) + self._clock_skew_seconds:
            raise JWTError("Account token was issued in the future")
        try:
            UUID(payload["sub"])
        except ValueError as exc:
            raise JWTError("Invalid account token subject") from exc
        return payload
