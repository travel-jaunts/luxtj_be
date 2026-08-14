from dataclasses import dataclass

from luxtj.contexts.account.domain.enums import AccountStatus, AuthFlowType


@dataclass(frozen=True)
class RequestOtpCommand:
    dial_code: str
    phone_number: str
    email: str | None = None


@dataclass(frozen=True)
class VerifyOtpCommand:
    dial_code: str
    phone_number: str
    otp: str
    flow_type: AuthFlowType
    email: str | None = None


@dataclass(frozen=True)
class RefreshTokenCommand:
    refresh_token: str


@dataclass(frozen=True)
class RevokeRefreshTokenCommand:
    refresh_token: str


@dataclass(frozen=True)
class RevokeAccountSessionsCommand:
    account_id: str


@dataclass(frozen=True)
class ChangeAccountStatusCommand:
    account_id: str
    target_status: AccountStatus
    actor_id: str | None
    reason: str
