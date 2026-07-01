from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from luxtj.contexts.account.application.ports import (
    AccountRepository,
    OtpChallengeRepository,
    SmsOtpSender,
    TokenIssuer,
)
from luxtj.contexts.account.application.security import OtpSecurityService
from luxtj.contexts.account.application.use_cases import (
    RequestLoginOtp,
    RequestSignupOtp,
    VerifyOtp,
)
from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class FakeClock:
    def __init__(self) -> None:
        self._now = datetime(2026, 1, 1, tzinfo=UTC)

    def utcnow(self) -> datetime:
        return self._now

    def advance_seconds(self, seconds: int) -> None:
        self._now = self._now + timedelta(seconds=seconds)


class InMemoryAccountRepository(AccountRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, Account] = {}

    async def add(self, account: Account) -> None:
        self._items[account.id] = account

    async def get_by_phone_identity(self, phone_identity: PhoneIdentity) -> Account | None:
        for account in self._items.values():
            if account.phone_identity == phone_identity:
                return account
        return None

    async def save(self, account: Account) -> None:
        self._items[account.id] = account


class InMemoryOtpChallengeRepository(OtpChallengeRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, OtpChallenge] = {}

    async def add(self, challenge: OtpChallenge) -> None:
        self._items[challenge.id] = challenge

    async def find_latest_for_flow(
        self,
        *,
        phone_identity: PhoneIdentity,
        flow_type: AuthFlowType,
    ) -> OtpChallenge | None:
        matches = [
            c
            for c in self._items.values()
            if c.phone_identity == phone_identity and c.flow_type == flow_type
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda c: c.created_at)[-1]

    async def save(self, challenge: OtpChallenge) -> None:
        self._items[challenge.id] = challenge


class CapturingSmsSender(SmsOtpSender):
    def __init__(self) -> None:
        self.sent: list[tuple[PhoneIdentity, str, AuthFlowType]] = []

    async def send_otp(
        self, *, phone_identity: PhoneIdentity, otp: str, flow_type: AuthFlowType
    ) -> None:
        self.sent.append((phone_identity, otp, flow_type))


class StaticTokenIssuer(TokenIssuer):
    async def issue_pair(
        self, *, account_id: UUID, phone_identity: PhoneIdentity
    ) -> tuple[str, str]:
        return (f"access-{account_id}", f"refresh-{account_id}")


@dataclass
class AuthFixtureBundle:
    clock: FakeClock
    account_repository: InMemoryAccountRepository
    challenge_repository: InMemoryOtpChallengeRepository
    sms_sender: CapturingSmsSender
    token_issuer: StaticTokenIssuer
    otp_security: OtpSecurityService


@pytest.fixture
def auth_bundle() -> AuthFixtureBundle:
    return AuthFixtureBundle(
        clock=FakeClock(),
        account_repository=InMemoryAccountRepository(),
        challenge_repository=InMemoryOtpChallengeRepository(),
        sms_sender=CapturingSmsSender(),
        token_issuer=StaticTokenIssuer(),
        otp_security=OtpSecurityService(pepper="test-pepper"),
    )


@pytest.fixture
def request_signup_otp_use_case(auth_bundle: AuthFixtureBundle) -> RequestSignupOtp:
    return RequestSignupOtp(
        challenge_repository=auth_bundle.challenge_repository,
        sms_sender=auth_bundle.sms_sender,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
        otp_ttl_seconds=300,
        otp_max_attempts=5,
    )


@pytest.fixture
def request_login_otp_use_case(auth_bundle: AuthFixtureBundle) -> RequestLoginOtp:
    return RequestLoginOtp(
        challenge_repository=auth_bundle.challenge_repository,
        sms_sender=auth_bundle.sms_sender,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
        otp_ttl_seconds=300,
        otp_max_attempts=5,
    )


@pytest.fixture
def verify_otp_use_case(auth_bundle: AuthFixtureBundle) -> VerifyOtp:
    return VerifyOtp(
        account_repository=auth_bundle.account_repository,
        challenge_repository=auth_bundle.challenge_repository,
        token_issuer=auth_bundle.token_issuer,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
    )
