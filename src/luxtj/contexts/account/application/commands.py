from dataclasses import dataclass

from luxtj.contexts.account.domain.enums import AuthFlowType


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
