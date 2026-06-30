import pytest

from luxtj.contexts.account.application.security import OtpSecurityService
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.errors import (
    OtpAttemptsExceededError,
    OtpConsumedError,
    OtpExpiredError,
)
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


def test_hash_and_verify_round_trip() -> None:
    security = OtpSecurityService(pepper="test-pepper")
    otp = "123456"

    hashed = security.hash_otp(otp)

    assert security.verify_otp(otp=otp, otp_hash=hashed.otp_hash, otp_salt=hashed.otp_salt)
    assert not security.verify_otp(otp="000000", otp_hash=hashed.otp_hash, otp_salt=hashed.otp_salt)


def test_otp_expiry_and_attempts_and_consume(auth_bundle) -> None:
    challenge = OtpChallenge.issue(
        phone_identity=PhoneIdentity("+91", "9876543210"),
        flow_type=AuthFlowType.LOGIN,
        otp_hash="hash",
        otp_salt="salt",
        now=auth_bundle.clock.utcnow(),
        ttl_seconds=10,
        max_attempts=1,
    )

    challenge.assert_available_for_verification(now=auth_bundle.clock.utcnow())
    challenge.register_failed_attempt()

    with pytest.raises(OtpAttemptsExceededError):
        challenge.assert_available_for_verification(now=auth_bundle.clock.utcnow())

    challenge.attempts_left = 1
    challenge.mark_consumed(now=auth_bundle.clock.utcnow())

    with pytest.raises(OtpConsumedError):
        challenge.assert_available_for_verification(now=auth_bundle.clock.utcnow())

    challenge.consumed_at = None
    auth_bundle.clock.advance_seconds(11)

    with pytest.raises(OtpExpiredError):
        challenge.assert_available_for_verification(now=auth_bundle.clock.utcnow())
