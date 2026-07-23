from twilio.rest import Client

from luxtj.contexts.account.application.ports import SmsOtpSender
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class TwilioSmsOtpSender(SmsOtpSender):
    def __init__(
        self,
        *,
        client: Client,
        from_phone: str,
    ) -> None:
        self._client = client
        self._from_phone = from_phone

    async def send_otp(
        self,
        *,
        phone_identity: PhoneIdentity,
        otp: str,
        flow_type: AuthFlowType,
    ) -> None:
        print(
            f"OTP delivery fallback sender | phone={phone_identity.e164_like} "
            f"flow={flow_type.value} otp={otp}"
        )
        if flow_type == AuthFlowType.SIGNUP:
            body = f"Your LuxTJ signup verification code is {otp}. This code expires soon."
        else:
            body = f"Your LuxTJ login code is {otp}. This code expires soon."
        await self._client.messages.create_async(
            to=phone_identity.e164_like,
            from_=self._from_phone,
            body=body,
        )
