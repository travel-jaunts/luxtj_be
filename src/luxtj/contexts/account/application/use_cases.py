import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from jose import JWTError

from luxtj.contexts.account.application.commands import (
    ChangeAccountStatusCommand,
    RefreshTokenCommand,
    RequestOtpCommand,
    RevokeAccountSessionsCommand,
    RevokeRefreshTokenCommand,
    VerifyOtpCommand,
)
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
from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AccountStatus, AuthFlowType
from luxtj.contexts.account.domain.errors import (
    InvalidAccountStatusError,
    InvalidRefreshTokenError,
    OtpChallengeNotFoundError,
    OtpDeliveryUnavailableError,
    OtpInvalidError,
)
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.refresh_session import RefreshSession
from luxtj.contexts.account.domain.status_change import AccountStatusChange
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
            "Generated OTP for %s flow",
            AuthFlowType.SIGNUP.value,
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
        try:
            await self._sms_sender.send_otp(
                phone_identity=phone_identity,
                otp=otp,
                flow_type=AuthFlowType.SIGNUP,
            )
        except OtpDeliveryUnavailableError:
            raise
        except Exception as exc:
            logger.warning("OTP delivery failed for signup flow")
            raise OtpDeliveryUnavailableError("OTP delivery is temporarily unavailable") from exc
        await self._challenge_repository.add(challenge)


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
            "Generated OTP for %s flow",
            AuthFlowType.LOGIN.value,
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
        try:
            await self._sms_sender.send_otp(
                phone_identity=phone_identity,
                otp=otp,
                flow_type=AuthFlowType.LOGIN,
            )
        except OtpDeliveryUnavailableError:
            raise
        except Exception as exc:
            logger.warning("OTP delivery failed for login flow")
            raise OtpDeliveryUnavailableError("OTP delivery is temporarily unavailable") from exc
        await self._challenge_repository.add(challenge)


class VerifyOtp:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        customer_profile_initializer: CustomerProfileInitializer,
        challenge_repository: OtpChallengeRepository,
        refresh_session_repository: RefreshSessionRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        otp_security: OtpSecurityService,
    ) -> None:
        self._account_repository = account_repository
        self._customer_profile_initializer = customer_profile_initializer
        self._challenge_repository = challenge_repository
        self._refresh_session_repository = refresh_session_repository
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
            await self._challenge_repository.decrement_attempt_if_available(
                challenge_id=challenge.id,
                expected_attempts_left=challenge.attempts_left,
            )
            raise OtpInvalidError("invalid otp")

        account = await self._account_repository.get_by_phone_identity(phone_identity)
        if account is not None and account.status.value != "ACTIVE":
            raise InvalidAccountStatusError("account is not active")

        consumed = await self._challenge_repository.consume_if_available(
            challenge_id=challenge.id,
            now=now,
        )
        if not consumed:
            raise OtpInvalidError("invalid otp")

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
        await self._save_refresh_session(refresh_token=refresh_token, account_id=account.id)
        return AuthTokenPairDTO(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def _save_refresh_session(self, *, refresh_token: str, account_id: UUID) -> None:
        payload = self._token_issuer.decode_refresh_token(refresh_token)
        issued_at = datetime.fromtimestamp(int(payload["iat"]), tz=UTC)
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
        await self._refresh_session_repository.add(
            RefreshSession.create(
                account_id=account_id,
                token_id=str(payload["jti"]),
                token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
                issued_at=issued_at,
                expires_at=expires_at,
            )
        )


class RefreshAccountTokens:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        token_issuer: TokenIssuer,
        refresh_session_repository: RefreshSessionRepository,
        clock: Clock,
    ) -> None:
        self._account_repository = account_repository
        self._token_issuer = token_issuer
        self._refresh_session_repository = refresh_session_repository
        self._clock = clock

    async def __call__(self, command: RefreshTokenCommand) -> AuthTokenPairDTO:
        try:
            payload = self._token_issuer.decode_refresh_token(command.refresh_token)
            account_id = UUID(str(payload["sub"]))
            token_id = str(payload["jti"])
        except (JWTError, KeyError, TypeError, ValueError) as exc:
            raise InvalidRefreshTokenError("invalid or expired account refresh token") from exc

        session = await self._refresh_session_repository.get_by_token_id(token_id)
        if session is None:
            raise InvalidRefreshTokenError("invalid or expired account refresh token")
        if session.account_id != account_id:
            raise InvalidRefreshTokenError("invalid or expired account refresh token")
        if session.revoked_at is not None or session.rotated_at is not None:
            await self._refresh_session_repository.revoke_all_for_account(
                account_id=account_id,
                now=self._clock.utcnow(),
            )
            raise InvalidRefreshTokenError("invalid or expired account refresh token")

        if hashlib.sha256(command.refresh_token.encode()).hexdigest() != session.token_hash:
            raise InvalidRefreshTokenError("invalid or expired account refresh token")

        account = await self._account_repository.get_by_id(account_id)
        if account is None:
            raise InvalidRefreshTokenError("account not found")
        if account.status.value != "ACTIVE":
            raise InvalidRefreshTokenError("account is not active")

        access_token, refresh_token = await self._token_issuer.issue_pair(
            account_id=account.id,
            phone_identity=account.phone_identity,
        )
        now = self._clock.utcnow()
        replacement_payload = self._token_issuer.decode_refresh_token(refresh_token)
        rotated = await self._refresh_session_repository.rotate(
            session_id=session.id,
            now=now,
            replacement_token_id=str(replacement_payload["jti"]),
        )
        if not rotated:
            raise InvalidRefreshTokenError("invalid or expired account refresh token")
        await self._refresh_session_repository.add(
            RefreshSession.create(
                account_id=account.id,
                token_id=str(replacement_payload["jti"]),
                token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
                issued_at=datetime.fromtimestamp(int(replacement_payload["iat"]), tz=UTC),
                expires_at=datetime.fromtimestamp(int(replacement_payload["exp"]), tz=UTC),
            )
        )
        return AuthTokenPairDTO(access_token=access_token, refresh_token=refresh_token)


class RevokeRefreshSession:
    def __init__(
        self,
        *,
        refresh_session_repository: RefreshSessionRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._refresh_session_repository = refresh_session_repository
        self._token_issuer = token_issuer
        self._clock = clock

    async def __call__(self, command: RevokeRefreshTokenCommand) -> None:
        try:
            payload = self._token_issuer.decode_refresh_token(command.refresh_token)
            session = await self._refresh_session_repository.get_by_token_id(str(payload["jti"]))
        except JWTError, KeyError, TypeError, ValueError:
            return
        if session is None:
            return
        if hashlib.sha256(command.refresh_token.encode()).hexdigest() != session.token_hash:
            return
        await self._refresh_session_repository.revoke(
            session_id=session.id,
            now=self._clock.utcnow(),
        )


class RevokeAccountSessions:
    def __init__(
        self, *, refresh_session_repository: RefreshSessionRepository, clock: Clock
    ) -> None:
        self._refresh_session_repository = refresh_session_repository
        self._clock = clock

    async def __call__(self, command: RevokeAccountSessionsCommand) -> None:
        await self._refresh_session_repository.revoke_all_for_account(
            account_id=UUID(command.account_id),
            now=self._clock.utcnow(),
        )


class ChangeAccountStatus:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        status_change_repository: AccountStatusChangeRepository,
        clock: Clock,
    ) -> None:
        self._account_repository = account_repository
        self._status_change_repository = status_change_repository
        self._clock = clock

    async def __call__(self, command: ChangeAccountStatusCommand) -> AccountStatus:
        account = await self._account_repository.get_by_id(UUID(command.account_id))
        if account is None:
            raise ValueError("account not found")
        reason = command.reason.strip()
        if not reason:
            raise ValueError("status change reason is required")

        previous_status = account.status
        now = self._clock.utcnow()
        if command.target_status == AccountStatus.ACTIVE:
            account.reenable(now=now)
        elif command.target_status == AccountStatus.SUSPENDED:
            account.suspend(now=now)
        elif command.target_status == AccountStatus.DISABLED:
            account.disable(now=now)
        else:
            raise ValueError("unsupported account status")

        await self._account_repository.save(account)
        await self._status_change_repository.add(
            AccountStatusChange.create(
                account_id=account.id,
                actor_id=command.actor_id,
                reason=reason,
                from_status=previous_status,
                to_status=account.status,
                changed_at=now,
            )
        )
        return account.status


class GetAccountStatus:
    def __init__(self, *, account_repository: AccountRepository) -> None:
        self._account_repository = account_repository

    async def __call__(self, account_id: UUID) -> AccountStatus:
        account = await self._account_repository.get_by_id(account_id)
        if account is None:
            raise ValueError("account not found")
        return account.status
