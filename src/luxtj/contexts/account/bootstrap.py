from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.http.async_http_client import AsyncTwilioHttpClient
from twilio.rest import Client

from luxtj.bootstrap import config
from luxtj.contexts.account.application.ports import (
    AccountRepository,
    Clock,
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
from luxtj.contexts.account.infrastructure.auth.jwt_token_issuer import JoseJwtTokenIssuer
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyOtpChallengeRepository,
)
from luxtj.contexts.account.infrastructure.sms.null_sender import NullSmsOtpSender
from luxtj.contexts.account.infrastructure.sms.twilio_sender import TwilioSmsOtpSender
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    twilio_client_handle,
)
from luxtj.utils import timeutils


class UtcClock(Clock):
    def utcnow(self) -> datetime:
        return timeutils.datetime_now()


def build_account_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AccountRepository:
    return SqlAlchemyAccountRepository(session)


def build_otp_challenge_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> OtpChallengeRepository:
    return SqlAlchemyOtpChallengeRepository(session)


def build_clock() -> Clock:
    return UtcClock()


def build_otp_security() -> OtpSecurityService:
    return OtpSecurityService(pepper=config.AUTH_OTP_PEPPER)


def build_sms_sender(
    twilio_client: Annotated[AsyncTwilioHttpClient, Depends(twilio_client_handle)],
) -> SmsOtpSender:
    if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_FROM_PHONE:
        return TwilioSmsOtpSender(
            client=Client(
                config.TWILIO_ACCOUNT_SID,
                config.TWILIO_AUTH_TOKEN,
                http_client=twilio_client,
            ),
            from_phone=config.TWILIO_FROM_PHONE,
        )
    return NullSmsOtpSender()


def build_token_issuer() -> TokenIssuer:
    return JoseJwtTokenIssuer(
        secret=config.AUTH_JWT_SECRET,
        algorithm=config.AUTH_JWT_ALGORITHM,
        access_ttl_seconds=config.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds=config.AUTH_REFRESH_TOKEN_TTL_SECONDS,
    )


def build_request_signup_otp(
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    sms_sender: Annotated[SmsOtpSender, Depends(build_sms_sender)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> RequestSignupOtp:
    return RequestSignupOtp(
        challenge_repository=challenge_repository,
        sms_sender=sms_sender,
        clock=clock,
        otp_security=otp_security,
        otp_ttl_seconds=config.AUTH_OTP_TTL_SECONDS,
        otp_max_attempts=config.AUTH_OTP_MAX_ATTEMPTS,
    )


def build_request_login_otp(
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    sms_sender: Annotated[SmsOtpSender, Depends(build_sms_sender)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> RequestLoginOtp:
    return RequestLoginOtp(
        challenge_repository=challenge_repository,
        sms_sender=sms_sender,
        clock=clock,
        otp_security=otp_security,
        otp_ttl_seconds=config.AUTH_OTP_TTL_SECONDS,
        otp_max_attempts=config.AUTH_OTP_MAX_ATTEMPTS,
    )


def build_verify_otp(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> VerifyOtp:
    return VerifyOtp(
        account_repository=account_repository,
        challenge_repository=challenge_repository,
        token_issuer=token_issuer,
        clock=clock,
        otp_security=otp_security,
    )
