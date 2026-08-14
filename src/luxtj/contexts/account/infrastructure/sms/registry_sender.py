"""SMS OTP sender that resolves Twilio / Telegram credentials from the integration registry."""

from __future__ import annotations

from httpx import AsyncClient
from twilio.http.async_http_client import AsyncTwilioHttpClient
from twilio.rest import Client

from luxtj.contexts.account.application.ports import SmsOtpSender
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.errors import OtpDeliveryUnavailableError
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.account.infrastructure.sms.null_sender import NullSmsOtpSender
from luxtj.contexts.account.infrastructure.sms.test_sender import TelegramSmsOtpSender
from luxtj.contexts.account.infrastructure.sms.twilio_sender import TwilioSmsOtpSender
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle

logger = get_logger_handle(__name__)


class RegistrySmsOtpSender(SmsOtpSender):
    """Prefer active Twilio, else active Telegram; never silently discard OTPs.

    Credentials and activation come from `other_apis` (admin Integrations), not env.
    """

    def __init__(
        self,
        *,
        twilio_http_client: AsyncTwilioHttpClient,
        http_client: AsyncClient,
        allow_test_sender: bool = False,
    ) -> None:
        self._twilio_http = twilio_http_client
        self._http = http_client
        self._allow_test_sender = allow_test_sender
        self._null = NullSmsOtpSender()

    def validate_configuration(self) -> bool:
        if self._twilio_sender() is not None or self._telegram_sender() is not None:
            return True
        if self._allow_test_sender:
            logger.warning("OTP test sender is enabled for this environment")
            return True
        logger.error("No approved SMS OTP provider is configured at startup")
        return False

    def _twilio_sender(self) -> TwilioSmsOtpSender | None:
        other = get_integration_registry().resolve_other_api("twilio")
        if other is None:
            return None
        configs = other.credential_configs()
        sid = credential_value(configs, "Account SID")
        token = credential_value(configs, "Auth Token")
        from_phone = credential_value(configs, "From Phone")
        if not (sid and token and from_phone):
            logger.warning("Twilio other_api active but credentials incomplete")
            return None
        return TwilioSmsOtpSender(
            client=Client(sid, token, http_client=self._twilio_http),
            from_phone=from_phone,
        )

    def _telegram_sender(self) -> TelegramSmsOtpSender | None:
        other = get_integration_registry().resolve_other_api("telegram")
        if other is None:
            return None
        configs = other.credential_configs()
        bot_token = credential_value(configs, "Bot Token")
        chat_id = credential_value(configs, "Chat ID")
        if not (bot_token and chat_id):
            logger.warning("Telegram other_api active but credentials incomplete")
            return None
        return TelegramSmsOtpSender(
            http_client=self._http,
            bot_token=bot_token,
            chat_id=chat_id,
        )

    async def send_otp(
        self,
        *,
        phone_identity: PhoneIdentity,
        otp: str,
        flow_type: AuthFlowType,
    ) -> None:
        twilio = self._twilio_sender()
        if twilio is not None:
            await twilio.send_otp(phone_identity=phone_identity, otp=otp, flow_type=flow_type)
            return
        telegram = self._telegram_sender()
        if telegram is not None:
            await telegram.send_otp(phone_identity=phone_identity, otp=otp, flow_type=flow_type)
            return
        if self._allow_test_sender:
            logger.warning("Using explicitly enabled OTP test sender")
            await self._null.send_otp(phone_identity=phone_identity, otp=otp, flow_type=flow_type)
            return
        logger.error("No approved SMS OTP provider is configured")
        raise OtpDeliveryUnavailableError("OTP delivery is temporarily unavailable")
