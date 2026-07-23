from fastapi import FastAPI
from fastapi.testclient import TestClient

from luxtj.contexts.account.application.use_cases import (
    RequestLoginOtp,
    VerifyOtp,
)
from luxtj.contexts.account.bootstrap import (
    build_request_login_otp,
    build_verify_otp,
)
from luxtj.contexts.account.presentation.http.router import account_auth_router
from luxtj.contexts.customer.application.use_cases import InitializeCustomerProfile


def _build_test_client(auth_bundle) -> TestClient:
    app = FastAPI()
    app.include_router(account_auth_router, prefix="/v1")

    login = RequestLoginOtp(
        challenge_repository=auth_bundle.challenge_repository,
        sms_sender=auth_bundle.sms_sender,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
        otp_ttl_seconds=300,
        otp_max_attempts=5,
    )
    verify = VerifyOtp(
        account_repository=auth_bundle.account_repository,
        customer_profile_initializer=InitializeCustomerProfile(
            bucket_list_repository=auth_bundle.bucket_list_repository,
            personal_calendar_repository=auth_bundle.personal_calendar_repository,
        ),
        challenge_repository=auth_bundle.challenge_repository,
        token_issuer=auth_bundle.token_issuer,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
    )

    app.dependency_overrides[build_request_login_otp] = lambda: login
    app.dependency_overrides[build_verify_otp] = lambda: verify

    return TestClient(app)


def test_login_request_and_verify_returns_token_pair_only(auth_bundle) -> None:
    client = _build_test_client(auth_bundle)

    request_resp = client.post(
        "/v1/auth/login",
        json={"dialCode": "+91", "phoneNumber": "9990001111"},
    )
    assert request_resp.status_code == 200
    assert request_resp.json()["status"] == "ok"

    otp = auth_bundle.sms_sender.sent[-1][1]
    verify_resp = client.post(
        "/v1/auth/verify",
        json={
            "dialCode": "+91",
            "phoneNumber": "9990001111",
            "otp": otp,
        },
    )

    assert verify_resp.status_code == 200
    payload = verify_resp.json()
    assert payload["status"] == "ok"
    assert "accessToken" in payload["output"]
    assert "refreshToken" in payload["output"]
    assert "account" not in payload["output"]


def test_verify_returns_internal_error_when_customer_profile_initialization_fails(
    auth_bundle,
    failing_customer_profile_initializer,
) -> None:
    app = FastAPI()
    app.include_router(account_auth_router, prefix="/v1")

    login = RequestLoginOtp(
        challenge_repository=auth_bundle.challenge_repository,
        sms_sender=auth_bundle.sms_sender,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
        otp_ttl_seconds=300,
        otp_max_attempts=5,
    )
    verify = VerifyOtp(
        account_repository=auth_bundle.account_repository,
        customer_profile_initializer=failing_customer_profile_initializer,
        challenge_repository=auth_bundle.challenge_repository,
        token_issuer=auth_bundle.token_issuer,
        clock=auth_bundle.clock,
        otp_security=auth_bundle.otp_security,
    )

    app.dependency_overrides[build_request_login_otp] = lambda: login
    app.dependency_overrides[build_verify_otp] = lambda: verify

    client = TestClient(app, raise_server_exceptions=False)
    request_resp = client.post(
        "/v1/auth/login",
        json={"dialCode": "+91", "phoneNumber": "9990001111"},
    )
    assert request_resp.status_code == 200

    otp = auth_bundle.sms_sender.sent[-1][1]
    verify_resp = client.post(
        "/v1/auth/verify",
        json={
            "dialCode": "+91",
            "phoneNumber": "9990001111",
            "otp": otp,
        },
    )

    assert verify_resp.status_code == 500
