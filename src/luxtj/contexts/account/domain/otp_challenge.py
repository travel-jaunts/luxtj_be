from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.errors import (
    OtpAttemptsExceededError,
    OtpConsumedError,
    OtpExpiredError,
)
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


@dataclass
class OtpChallenge:
    id: UUID
    phone_identity: PhoneIdentity
    flow_type: AuthFlowType
    otp_hash: str
    otp_salt: str
    expires_at: datetime
    attempts_left: int
    consumed_at: datetime | None
    created_at: datetime

    @classmethod
    def issue(
        cls,
        *,
        phone_identity: PhoneIdentity,
        flow_type: AuthFlowType,
        otp_hash: str,
        otp_salt: str,
        now: datetime,
        ttl_seconds: int,
        max_attempts: int,
    ) -> OtpChallenge:
        return cls(
            id=uuid4(),
            phone_identity=phone_identity,
            flow_type=flow_type,
            otp_hash=otp_hash,
            otp_salt=otp_salt,
            expires_at=now + timedelta(seconds=ttl_seconds),
            attempts_left=max_attempts,
            consumed_at=None,
            created_at=now,
        )

    def assert_available_for_verification(self, *, now: datetime) -> None:
        if self.consumed_at is not None:
            raise OtpConsumedError("otp already consumed")
        if now >= self.expires_at:
            raise OtpExpiredError("otp expired")
        if self.attempts_left <= 0:
            raise OtpAttemptsExceededError("otp attempts exceeded")

    def register_failed_attempt(self) -> None:
        self.attempts_left = max(0, self.attempts_left - 1)

    def mark_consumed(self, *, now: datetime) -> None:
        self.consumed_at = now
