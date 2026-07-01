from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class NullSmsOtpSender:
    async def send_otp(
        self, *, phone_identity: PhoneIdentity, otp: str, flow_type: AuthFlowType
    ) -> None:
        print(
            f"OTP delivery fallback sender | phone={phone_identity.e164_like} "
            f"flow={flow_type.value} otp={otp}"
        )
