from httpx import AsyncClient

from luxtj.contexts.account.application.ports import SmsOtpSender
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class TestSmsOtpSender(SmsOtpSender):
    def __init__(self, test_provider: SmsOtpSender) -> None:
        self._test_provider = test_provider

    async def send_otp(
        self,
        *,
        phone_identity: PhoneIdentity,
        otp: str,
        flow_type: AuthFlowType,
    ) -> None:
        return await self._test_provider.send_otp(
            phone_identity=phone_identity,
            otp=otp,
            flow_type=flow_type,
        )


class TelegramSmsOtpSender(SmsOtpSender):
    def __init__(self, http_client: AsyncClient, bot_token: str, chat_id: str) -> None:
        self._http_client = http_client
        self._bot_token = bot_token
        self._chat_id = chat_id

    async def send_otp(
        self,
        *,
        phone_identity: PhoneIdentity,
        otp: str,
        flow_type: AuthFlowType,
    ) -> None:
        sms_body: str = (
            f"OTP delivery fallback sender | phone={phone_identity.e164_like} "
            f"flow={flow_type.value} otp={otp}"
        )
        print(sms_body)

        response = await self._http_client.post(
            f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            json={
                "chat_id": self._chat_id,
                "text": sms_body,
            },
        )
        return await response.raise_for_status().aclose()
