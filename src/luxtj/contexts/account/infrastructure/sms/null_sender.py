from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class NullSmsOtpSender:
    async def send_otp(
        self, *, phone_identity: PhoneIdentity, otp: str, flow_type: AuthFlowType
    ) -> None:
        print(
            f"OTP delivery test sender | flow={flow_type.value} | phone={phone_identity.dial_code}{phone_identity.phone_number} | otp={otp}"
        )
