import pytest

from luxtj.contexts.account.application.commands import RequestOtpCommand, VerifyOtpCommand
from luxtj.contexts.account.application.use_cases import VerifyOtp
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


async def test_request_login_then_verify_auto_creates_account(
    auth_bundle,
    request_login_otp_use_case,
    verify_otp_use_case,
) -> None:
    await request_login_otp_use_case(RequestOtpCommand(dial_code="+91", phone_number="9876543210"))
    assert len(auth_bundle.sms_sender.sent) == 1

    sent_phone, sent_otp, sent_flow = auth_bundle.sms_sender.sent[0]
    assert sent_phone == PhoneIdentity("+91", "9876543210")
    assert sent_flow == AuthFlowType.LOGIN

    tokens = await verify_otp_use_case(
        VerifyOtpCommand(
            dial_code="+91",
            phone_number="9876543210",
            otp=sent_otp,
            flow_type=AuthFlowType.LOGIN,
            email="new@example.com",
        )
    )

    account = await auth_bundle.account_repository.get_by_phone_identity(
        PhoneIdentity("+91", "9876543210")
    )
    assert account is not None
    assert account.email == "new@example.com"
    bucket_list = await auth_bundle.bucket_list_repository.get_by_account_id(account.id)
    assert bucket_list is not None
    calendar = await auth_bundle.personal_calendar_repository.get_by_account_id(account.id)
    assert calendar is not None
    assert tokens.access_token.startswith("access-")
    assert tokens.refresh_token.startswith("refresh-")


async def test_verify_otp_raises_when_customer_profile_initialization_fails(
    auth_bundle,
    request_login_otp_use_case,
    failing_customer_profile_initializer,
) -> None:
    verify_otp_use_case = VerifyOtp(
        account_repository=auth_bundle.account_repository,
        customer_profile_initializer=failing_customer_profile_initializer,
        challenge_repository=auth_bundle.challenge_repository,
        token_issuer=auth_bundle.token_issuer,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
    )

    await request_login_otp_use_case(RequestOtpCommand(dial_code="+91", phone_number="9876543210"))
    sent_otp = auth_bundle.sms_sender.sent[-1][1]

    with pytest.raises(RuntimeError, match="failed to initialize customer profile"):
        await verify_otp_use_case(
            VerifyOtpCommand(
                dial_code="+91",
                phone_number="9876543210",
                otp=sent_otp,
                flow_type=AuthFlowType.LOGIN,
                email="new@example.com",
            )
        )


async def test_email_backfill_only_when_empty(
    auth_bundle,
    request_login_otp_use_case,
    verify_otp_use_case,
) -> None:
    await request_login_otp_use_case(RequestOtpCommand(dial_code="+1", phone_number="5551010"))
    first_otp = auth_bundle.sms_sender.sent[-1][1]
    await verify_otp_use_case(
        VerifyOtpCommand(
            dial_code="+1",
            phone_number="5551010",
            otp=first_otp,
            flow_type=AuthFlowType.LOGIN,
            email="first@example.com",
        )
    )

    await request_login_otp_use_case(RequestOtpCommand(dial_code="+1", phone_number="5551010"))
    second_otp = auth_bundle.sms_sender.sent[-1][1]
    await verify_otp_use_case(
        VerifyOtpCommand(
            dial_code="+1",
            phone_number="5551010",
            otp=second_otp,
            flow_type=AuthFlowType.LOGIN,
            email="second@example.com",
        )
    )

    account = await auth_bundle.account_repository.get_by_phone_identity(
        PhoneIdentity("+1", "5551010")
    )
    assert account is not None
    assert account.email == "first@example.com"
