from typing import Annotated
import logging

from fastapi import APIRouter, Body, Depends

from common.serializerlib import (
    ApiSerializerBaseModel,
    ApiSuccessResponse,
    RequestProcessStatus,
)

from luxtj.service import AuthenticationService, TelecomServiceProvider, UserAccountsServiceProvider

idam_router = APIRouter(prefix="/idam")


def get_telecom_service() -> TelecomServiceProvider:
    """Dependency to provide TelecomServiceProvider instance"""
    return TelecomServiceProvider()


def get_user_accounts_service() -> UserAccountsServiceProvider:
    """Dependency to provide UserAccountsServiceProvider instance"""
    return UserAccountsServiceProvider()


def get_authentication_service(
    telecom_service: Annotated[TelecomServiceProvider, Depends(get_telecom_service)],
    user_accounts_service: Annotated[UserAccountsServiceProvider, Depends(get_user_accounts_service)],
) -> AuthenticationService:
    """Dependency to provide AuthenticationService instance"""
    return AuthenticationService(
        telecom_service=telecom_service,
        user_accounts_service=user_accounts_service,
        logger=logging.getLogger(__name__)
    )


class AuthenticatedUserResponse(ApiSerializerBaseModel):
    message: str


class PhoneDetailsBody(ApiSerializerBaseModel):
    phone_number: str
    country_dial_code: str

@idam_router.post(
    "/login-request-otp",
    response_model=ApiSuccessResponse[AuthenticatedUserResponse],
    status_code=200,
    summary="Authenticate user and return user details",
    name="User Login",
)
async def login(
    cell_details: Annotated[PhoneDetailsBody, Body(...)],
    authentication_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> ApiSuccessResponse[AuthenticatedUserResponse]:
    """
    Authenticate user with phone number and return user details
    """
    await authentication_service.login(
        country_dial_code=cell_details.country_dial_code,
        phone_number=cell_details.phone_number,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=AuthenticatedUserResponse(
            message="OTP sent to the phone number if it is valid and registered"
        ),
    )
