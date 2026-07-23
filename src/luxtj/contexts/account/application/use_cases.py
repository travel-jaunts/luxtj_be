import logging
from dataclasses import dataclass

from luxtj.contexts.account.application.commands import RequestOtpCommand, VerifyOtpCommand
from luxtj.contexts.account.application.ports import (
    AccountRepository,
    Clock,
    CustomerProfileInitializer,
    OtpChallengeRepository,
    SmsOtpSender,
    TokenIssuer,
)
from luxtj.contexts.account.application.security import OtpSecurityService
from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.errors import (
    OtpChallengeNotFoundError,
    OtpInvalidError,
)
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.value_objects import PhoneIdentity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthTokenPairDTO:
    access_token: str
    refresh_token: str


class RequestSignupOtp:
    def __init__(
        self,
        *,
        challenge_repository: OtpChallengeRepository,
        sms_sender: SmsOtpSender,
        clock: Clock,
        otp_security: OtpSecurityService,
        otp_ttl_seconds: int,
        otp_max_attempts: int,
    ) -> None:
        self._challenge_repository = challenge_repository
        self._sms_sender = sms_sender
        self._clock = clock
        self._otp_security = otp_security
        self._otp_ttl_seconds = otp_ttl_seconds
        self._otp_max_attempts = otp_max_attempts

    async def __call__(self, command: RequestOtpCommand) -> None:
        phone_identity = PhoneIdentity(command.dial_code, command.phone_number)
        otp = self._otp_security.generate_otp()
        logger.info(
            "[DEV] Generated OTP for %s flow phone=%s otp=%s",
            AuthFlowType.SIGNUP.value,
            phone_identity.e164_like,
            otp,
        )
        hash_result = self._otp_security.hash_otp(otp)
        challenge = OtpChallenge.issue(
            phone_identity=phone_identity,
            flow_type=AuthFlowType.SIGNUP,
            otp_hash=hash_result.otp_hash,
            otp_salt=hash_result.otp_salt,
            now=self._clock.utcnow(),
            ttl_seconds=self._otp_ttl_seconds,
            max_attempts=self._otp_max_attempts,
        )
        await self._challenge_repository.add(challenge)
        await self._sms_sender.send_otp(
            phone_identity=phone_identity,
            otp=otp,
            flow_type=AuthFlowType.SIGNUP,
        )


class RequestLoginOtp:
    def __init__(
        self,
        *,
        challenge_repository: OtpChallengeRepository,
        sms_sender: SmsOtpSender,
        clock: Clock,
        otp_security: OtpSecurityService,
        otp_ttl_seconds: int,
        otp_max_attempts: int,
    ) -> None:
        self._challenge_repository = challenge_repository
        self._sms_sender = sms_sender
        self._clock = clock
        self._otp_security = otp_security
        self._otp_ttl_seconds = otp_ttl_seconds
        self._otp_max_attempts = otp_max_attempts

    async def __call__(self, command: RequestOtpCommand) -> None:
        phone_identity = PhoneIdentity(command.dial_code, command.phone_number)
        otp = self._otp_security.generate_otp()
        logger.info(
            "[DEV] Generated OTP for %s flow phone=%s otp=%s",
            AuthFlowType.LOGIN.value,
            phone_identity.e164_like,
            otp,
        )
        hash_result = self._otp_security.hash_otp(otp)
        challenge = OtpChallenge.issue(
            phone_identity=phone_identity,
            flow_type=AuthFlowType.LOGIN,
            otp_hash=hash_result.otp_hash,
            otp_salt=hash_result.otp_salt,
            now=self._clock.utcnow(),
            ttl_seconds=self._otp_ttl_seconds,
            max_attempts=self._otp_max_attempts,
        )
        await self._challenge_repository.add(challenge)
        await self._sms_sender.send_otp(
            phone_identity=phone_identity,
            otp=otp,
            flow_type=AuthFlowType.LOGIN,
        )


class VerifyOtp:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        customer_profile_initializer: CustomerProfileInitializer,
        challenge_repository: OtpChallengeRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        otp_security: OtpSecurityService,
    ) -> None:
        self._account_repository = account_repository
        self._customer_profile_initializer = customer_profile_initializer
        self._challenge_repository = challenge_repository
        self._token_issuer = token_issuer
        self._clock = clock
        self._otp_security = otp_security

    async def __call__(self, command: VerifyOtpCommand) -> AuthTokenPairDTO:
        phone_identity = PhoneIdentity(command.dial_code, command.phone_number)
        challenge = await self._challenge_repository.find_latest_for_flow(
            phone_identity=phone_identity,
            flow_type=command.flow_type,
        )
        if challenge is None:
            raise OtpChallengeNotFoundError("otp challenge not found")

        now = self._clock.utcnow()
        challenge.assert_available_for_verification(now=now)

        is_valid = self._otp_security.verify_otp(
            otp=command.otp,
            otp_hash=challenge.otp_hash,
            otp_salt=challenge.otp_salt,
        )
        if not is_valid:
            challenge.register_failed_attempt()
            await self._challenge_repository.save(challenge)
            raise OtpInvalidError("invalid otp")

        challenge.mark_consumed(now=now)
        await self._challenge_repository.save(challenge)

        account = await self._account_repository.get_by_phone_identity(phone_identity)
        if account is None:
            account = Account.create(
                phone_identity=phone_identity,
                now=now,
                email=command.email,
            )
            await self._account_repository.add(account)
            await self._customer_profile_initializer(account.id)
        elif account.backfill_email_if_empty(command.email, now=now):
            await self._account_repository.save(account)

        access_token, refresh_token = await self._token_issuer.issue_pair(
            account_id=account.id,
            phone_identity=phone_identity,
        )
        return AuthTokenPairDTO(
            access_token=access_token,
            refresh_token=refresh_token,
        )
