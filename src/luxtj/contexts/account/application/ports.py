from datetime import datetime
from typing import Protocol
from uuid import UUID

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class AccountRepository(Protocol):
    async def add(self, account: Account) -> None: ...
    async def get_by_phone_identity(self, phone_identity: PhoneIdentity) -> Account | None: ...
    async def save(self, account: Account) -> None: ...


class OtpChallengeRepository(Protocol):
    async def add(self, challenge: OtpChallenge) -> None: ...
    async def find_latest_for_flow(
        self, *, phone_identity: PhoneIdentity, flow_type: AuthFlowType
    ) -> OtpChallenge | None: ...
    async def save(self, challenge: OtpChallenge) -> None: ...


class SmsOtpSender(Protocol):
    async def send_otp(
        self, *, phone_identity: PhoneIdentity, otp: str, flow_type: AuthFlowType
    ) -> None: ...


class TokenIssuer(Protocol):
    async def issue_pair(
        self, *, account_id: UUID, phone_identity: PhoneIdentity
    ) -> tuple[str, str]: ...


class Clock(Protocol):
    def utcnow(self) -> datetime: ...
