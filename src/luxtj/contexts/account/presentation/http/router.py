from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from luxtj.contexts.account.application.commands import (
    RefreshTokenCommand,
    RequestOtpCommand,
    RevokeAccountSessionsCommand,
    RevokeRefreshTokenCommand,
    VerifyOtpCommand,
)
from luxtj.contexts.account.application.use_cases import (
    GetAccountStatus,
    RefreshAccountTokens,
    RequestLoginOtp,
    RevokeAccountSessions,
    RevokeRefreshSession,
    VerifyOtp,
)
from luxtj.contexts.account.bootstrap import (
    build_get_account_status,
    build_refresh_account_tokens,
    build_request_login_otp,
    build_revoke_account_sessions,
    build_revoke_refresh_session,
    build_verify_otp,
)
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.errors import AccountAuthError, OtpDeliveryUnavailableError
from luxtj.contexts.account.presentation.http.dependencies import (
    AccountPrincipal,
    get_current_account_principal,
)
from luxtj.contexts.account.presentation.http.schemas import (
    AccountStatusSerializer,
    RefreshTokenBody,
    RequestOtpBody,
    RequestOtpResultSerializer,
    TokenPairSerializer,
    VerifyOtpBody,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

account_auth_router = APIRouter(prefix="/auth", tags=["auth"])


@account_auth_router.post(
    "/user/login",
    response_model=ApiSuccessResponse[RequestOtpResultSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Request login OTP",
)
async def request_login_otp(
    use_case: Annotated[RequestLoginOtp, Depends(build_request_login_otp)],
    body: Annotated[RequestOtpBody, Body(...)],
) -> ApiSuccessResponse[RequestOtpResultSerializer] | ApiErrorResponse:
    try:
        await use_case(
            RequestOtpCommand(
                dial_code=body.dial_code,
                phone_number=body.phone_number,
                email=body.email,
            )
        )
    except OtpDeliveryUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="OTP delivery is temporarily unavailable"
        ) from exc
    except (ValueError, AccountAuthError) as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=RequestOtpResultSerializer(message="otp sent"),
    )


@account_auth_router.post(
    "/user/refresh",
    response_model=ApiSuccessResponse[TokenPairSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Refresh account token pair",
)
async def refresh_account_tokens(
    use_case: Annotated[RefreshAccountTokens, Depends(build_refresh_account_tokens)],
    body: Annotated[RefreshTokenBody, Body(...)],
) -> ApiSuccessResponse[TokenPairSerializer] | ApiErrorResponse:
    try:
        tokens = await use_case(RefreshTokenCommand(refresh_token=body.refresh_token))
    except AccountAuthError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=TokenPairSerializer.from_dto(tokens),
    )


@account_auth_router.post(
    "/user/logout",
    response_model=ApiSuccessResponse[RequestOtpResultSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Revoke current account refresh session",
)
async def revoke_refresh_session(
    use_case: Annotated[RevokeRefreshSession, Depends(build_revoke_refresh_session)],
    body: Annotated[RefreshTokenBody, Body(...)],
) -> ApiSuccessResponse[RequestOtpResultSerializer] | ApiErrorResponse:
    await use_case(RevokeRefreshTokenCommand(refresh_token=body.refresh_token))
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=RequestOtpResultSerializer(message="session revoked"),
    )


@account_auth_router.post(
    "/user/logout-all",
    response_model=ApiSuccessResponse[RequestOtpResultSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Revoke all account refresh sessions",
)
async def revoke_account_sessions(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[RevokeAccountSessions, Depends(build_revoke_account_sessions)],
) -> ApiSuccessResponse[RequestOtpResultSerializer] | ApiErrorResponse:
    await use_case(RevokeAccountSessionsCommand(account_id=str(principal.account_id)))
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=RequestOtpResultSerializer(message="sessions revoked"),
    )


@account_auth_router.get(
    "/user/status",
    response_model=ApiSuccessResponse[AccountStatusSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Inspect current account status",
)
async def get_account_status(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[GetAccountStatus, Depends(build_get_account_status)],
) -> ApiSuccessResponse[AccountStatusSerializer] | ApiErrorResponse:
    status = await use_case(principal.account_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AccountStatusSerializer(status=status),
    )


@account_auth_router.post(
    "/user/verify",
    response_model=ApiSuccessResponse[TokenPairSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Verify OTP and return token pair",
)
async def verify_otp(
    use_case: Annotated[VerifyOtp, Depends(build_verify_otp)],
    body: Annotated[VerifyOtpBody, Body(...)],
) -> ApiSuccessResponse[TokenPairSerializer] | ApiErrorResponse:
    try:
        tokens = await use_case(
            VerifyOtpCommand(
                dial_code=body.dial_code,
                phone_number=body.phone_number,
                otp=body.otp,
                flow_type=AuthFlowType.LOGIN,
                email=body.email,
            )
        )
    except OtpDeliveryUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="OTP delivery is temporarily unavailable"
        ) from exc
    except (ValueError, AccountAuthError) as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=TokenPairSerializer.from_dto(tokens),
    )
