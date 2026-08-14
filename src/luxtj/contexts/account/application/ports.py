from datetime import datetime
from typing import Protocol
from uuid import UUID

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.refresh_session import RefreshSession
from luxtj.contexts.account.domain.status_change import AccountStatusChange
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class AccountRepository(Protocol):
    async def add(self, account: Account) -> None: ...
    async def get_by_id(self, account_id: UUID) -> Account | None: ...
    async def get_by_phone_identity(self, phone_identity: PhoneIdentity) -> Account | None: ...
    async def save(self, account: Account) -> None: ...


class AccountStatusChangeRepository(Protocol):
    async def add(self, change: AccountStatusChange) -> None: ...


class OtpChallengeRepository(Protocol):
    async def add(self, challenge: OtpChallenge) -> None: ...
    async def find_latest_for_flow(
        self, *, phone_identity: PhoneIdentity, flow_type: AuthFlowType
    ) -> OtpChallenge | None: ...
    async def consume_if_available(self, *, challenge_id: UUID, now: datetime) -> bool: ...
    async def decrement_attempt_if_available(
        self, *, challenge_id: UUID, expected_attempts_left: int
    ) -> bool: ...
    async def save(self, challenge: OtpChallenge) -> None: ...


class SmsOtpSender(Protocol):
    async def send_otp(
        self, *, phone_identity: PhoneIdentity, otp: str, flow_type: AuthFlowType
    ) -> None: ...


class TokenIssuer(Protocol):
    async def issue_pair(
        self, *, account_id: UUID, phone_identity: PhoneIdentity
    ) -> tuple[str, str]: ...

    def decode_refresh_token(self, token: str) -> dict: ...


class RefreshSessionRepository(Protocol):
    async def add(self, session: RefreshSession) -> None: ...

    async def get_by_token_id(self, token_id: str) -> RefreshSession | None: ...

    async def rotate(
        self,
        *,
        session_id: UUID,
        now: datetime,
        replacement_token_id: str,
    ) -> bool: ...

    async def revoke(self, *, session_id: UUID, now: datetime) -> bool: ...

    async def revoke_all_for_account(self, *, account_id: UUID, now: datetime) -> int: ...

    async def delete_expired_revoked(self, *, before: datetime) -> int: ...


class CustomerProfileInitializer(Protocol):
    async def __call__(self, account_id: UUID) -> None: ...


class Clock(Protocol):
    def utcnow(self) -> datetime: ...
