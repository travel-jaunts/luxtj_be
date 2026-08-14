from datetime import datetime
from typing import Annotated

from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.http.async_http_client import AsyncTwilioHttpClient

from luxtj.bootstrap import config
from luxtj.contexts.account.application.ports import (
    AccountRepository,
    AccountStatusChangeRepository,
    Clock,
    CustomerProfileInitializer,
    OtpChallengeRepository,
    RefreshSessionRepository,
    SmsOtpSender,
    TokenIssuer,
)
from luxtj.contexts.account.application.security import OtpSecurityService
from luxtj.contexts.account.application.use_cases import (
    ChangeAccountStatus,
    GetAccountStatus,
    RefreshAccountTokens,
    RequestLoginOtp,
    RequestSignupOtp,
    RevokeAccountSessions,
    RevokeRefreshSession,
    VerifyOtp,
)
from luxtj.contexts.account.infrastructure.auth.jwt_token_issuer import JoseJwtTokenIssuer
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyAccountStatusChangeRepository,
    SqlAlchemyOtpChallengeRepository,
    SqlAlchemyRefreshSessionRepository,
)
from luxtj.contexts.account.infrastructure.sms.registry_sender import RegistrySmsOtpSender
from luxtj.contexts.customer.bootstrap import build_initialize_customer_profile
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
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


def build_refresh_session_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> RefreshSessionRepository:
    return SqlAlchemyRefreshSessionRepository(session)


def build_account_status_change_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AccountStatusChangeRepository:
    return SqlAlchemyAccountStatusChangeRepository(session)


def build_clock() -> Clock:
    return UtcClock()


def build_otp_security() -> OtpSecurityService:
    return OtpSecurityService(pepper=config.AUTH_OTP_PEPPER)


def build_sms_sender(
    twilio_client: Annotated[AsyncTwilioHttpClient, Depends(twilio_client_handle)],
    http_client: Annotated[AsyncClient, Depends(http_client_handle)],
) -> SmsOtpSender:
    return RegistrySmsOtpSender(
        twilio_http_client=twilio_client,
        http_client=http_client,
        allow_test_sender=(
            config.AUTH_OTP_ALLOW_TEST_SENDER and config.ENVIRONMENT in {"development", "test"}
        ),
    )


def build_token_issuer() -> TokenIssuer:
    return JoseJwtTokenIssuer(
        keys=config.AUTH_ACCOUNT_JWT_KEYS,
        active_kid=config.AUTH_ACCOUNT_JWT_ACTIVE_KID,
        algorithms=config.AUTH_JWT_ALLOWED_ALGORITHMS,
        issuer=config.AUTH_ACCOUNT_JWT_ISSUER,
        audience=config.AUTH_ACCOUNT_JWT_AUDIENCE,
        clock_skew_seconds=config.AUTH_JWT_CLOCK_SKEW_SECONDS,
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
    customer_profile_initializer: Annotated[
        CustomerProfileInitializer,
        Depends(build_initialize_customer_profile),
    ],
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> VerifyOtp:
    return VerifyOtp(
        account_repository=account_repository,
        customer_profile_initializer=customer_profile_initializer,
        challenge_repository=challenge_repository,
        refresh_session_repository=refresh_session_repository,
        token_issuer=token_issuer,
        clock=clock,
        otp_security=otp_security,
    )


def build_refresh_account_tokens(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RefreshAccountTokens:
    return RefreshAccountTokens(
        account_repository=account_repository,
        token_issuer=token_issuer,
        refresh_session_repository=refresh_session_repository,
        clock=clock,
    )


def build_revoke_refresh_session(
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RevokeRefreshSession:
    return RevokeRefreshSession(
        refresh_session_repository=refresh_session_repository,
        token_issuer=token_issuer,
        clock=clock,
    )


def build_revoke_account_sessions(
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RevokeAccountSessions:
    return RevokeAccountSessions(
        refresh_session_repository=refresh_session_repository,
        clock=clock,
    )


def build_change_account_status(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    status_change_repository: Annotated[
        AccountStatusChangeRepository,
        Depends(build_account_status_change_repository),
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ChangeAccountStatus:
    return ChangeAccountStatus(
        account_repository=account_repository,
        status_change_repository=status_change_repository,
        clock=clock,
    )


def build_get_account_status(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
) -> GetAccountStatus:
    return GetAccountStatus(account_repository=account_repository)
