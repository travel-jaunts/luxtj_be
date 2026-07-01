from typing import Annotated

from fastapi import APIRouter, Body, Depends

from luxtj.contexts.account.application.commands import RequestOtpCommand, VerifyOtpCommand
from luxtj.contexts.account.application.use_cases import (
    RequestLoginOtp,
    VerifyOtp,
)
from luxtj.contexts.account.bootstrap import (
    build_request_login_otp,
    build_verify_otp,
)
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.errors import AccountAuthError
from luxtj.contexts.account.presentation.http.schemas import (
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
    "/login",
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
    except (ValueError, AccountAuthError) as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=RequestOtpResultSerializer(message="otp sent"),
    )


@account_auth_router.post(
    "/verify",
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
    except (ValueError, AccountAuthError) as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=TokenPairSerializer.from_dto(tokens),
    )
