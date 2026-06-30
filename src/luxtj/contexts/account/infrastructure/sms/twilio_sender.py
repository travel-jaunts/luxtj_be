import asyncio

from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class TwilioSmsOtpSender:
    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_phone: str,
    ) -> None:
        from twilio.rest import Client

        self._client = Client(account_sid, auth_token)
        self._from_phone = from_phone

    async def send_otp(
        self,
        *,
        phone_identity: PhoneIdentity,
        otp: str,
        flow_type: AuthFlowType,
    ) -> None:
        body = f"Your LuxTJ verification code is {otp}. This code expires soon."
        await asyncio.to_thread(
            self._client.messages.create,
            to=phone_identity.e164_like,
            from_=self._from_phone,
            body=body,
        )
