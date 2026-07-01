from luxtj.contexts.account.application.commands import RequestOtpCommand, VerifyOtpCommand
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
    assert tokens.access_token.startswith("access-")
    assert tokens.refresh_token.startswith("refresh-")


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
