"""
Top level business services at luxtj
"""

from luxtj.protocols import ITelecomService, IUserAccountsService, ILogger
from luxtj.exceptions.authentication import (
    InvalidPhoneNumberException,
    PhoneNumberAlreadyRegisteredException,
    PhoneNumberNotRegisteredException,
)
from luxtj.domain.entity import LuxtjUser, LuxtjUserAuthorizationDetail

class AuthenticationService:
    def __init__(
        self,
        telecom_service: ITelecomService,
        user_accounts_service: IUserAccountsService,
        logger: ILogger,
    ):
        self.telecom_service = telecom_service
        self.user_accounts_service = user_accounts_service
        self.logger = logger

    async def login(self, country_dial_code: str, phone_number: str):
        """
        Handle login request
        """
        # check if the phone number is valid
        if not await self.telecom_service.is_valid_phone_number(country_dial_code, phone_number):
            raise InvalidPhoneNumberException(country_dial_code, phone_number)

        # check if the phone number is registered in repository
        if not await self.user_accounts_service.is_phone_number_registered(
            country_dial_code, phone_number
        ):
            new_user = await self.user_accounts_service.create_user_with_phone_number(
                country_dial_code, phone_number
            )
            self.logger.info(
                "NEW_USER_CREATED",
                extra={
                    "country_dial_code": country_dial_code,
                    "phone_number": phone_number,
                    "user_guid": new_user.guid,
                },
            )

        # send OTP to the phone number
        await self.telecom_service.send_otp(country_dial_code, phone_number)
        return None

    async def signup(self, country_dial_code: str, phone_number: str):
        """
        Handle signup request
        """
        # check if the phone number is valid
        if not await self.telecom_service.is_valid_phone_number(country_dial_code, phone_number):
            raise InvalidPhoneNumberException(country_dial_code, phone_number)

        # check if the phone number is registered in repository
        if not await self.user_accounts_service.is_phone_number_registered(
            country_dial_code, phone_number
        ):
            new_user = await self.user_accounts_service.create_user_with_phone_number(
                country_dial_code, phone_number
            )
            self.logger.info(
                "NEW_USER_CREATED",
                extra={
                    "country_dial_code": country_dial_code,
                    "phone_number": phone_number,
                    "user_guid": new_user.guid,
                },
            )
        else:
            old_user = await self.user_accounts_service.get_user_by_phone_number(
                country_dial_code, phone_number
            )
            self.logger.info(
                "PHONE_NUMBER_ALREADY_REGISTERED",
                extra={
                    "country_dial_code": country_dial_code,
                    "phone_number": phone_number,
                    "user_guid": old_user.guid,
                },
            )
            raise PhoneNumberAlreadyRegisteredException(country_dial_code, phone_number)

        # send OTP to the phone number
        await self.telecom_service.send_otp(country_dial_code, phone_number)
        return None

    async def verify_otp(self, country_dial_code: str, phone_number: str, otp: str):
        """
        Handle OTP verification request
        """
        # check if the phone number is valid
        if not await self.telecom_service.is_valid_phone_number(country_dial_code, phone_number):
            raise InvalidPhoneNumberException(country_dial_code, phone_number)

        # check if the phone number is registered in repository
        if not await self.user_accounts_service.is_phone_number_registered(
            country_dial_code, phone_number
        ):
            self.logger.info(
                "PHONE_NUMBER_NOT_REGISTERED",
                extra={"country_dial_code": country_dial_code, "phone_number": phone_number},
            )
            raise PhoneNumberNotRegisteredException(country_dial_code, phone_number)

        # verify the OTP
        if await self.telecom_service.verify_otp(country_dial_code, phone_number, otp):
            old_user = await self.user_accounts_service.get_user_by_phone_number(
                country_dial_code, phone_number
            )
            # generate login tokens and return it to the client
            authorization_tokens = await self.user_accounts_service.login_user_by_guid(
                old_user.guid
            )
            return authorization_tokens
        else:
            # return error message
            self.logger.info(
                "OTP_VERIFICATION_FAILED",
                extra={"country_dial_code": country_dial_code, "phone_number": phone_number},
            )
            return None


class TelecomServiceProvider(ITelecomService):

    def __init__(self):
        pass

    async def is_valid_phone_number(self, country_dial_code: str, phone_number: str) -> bool:
        raise NotImplementedError
    
    async def send_otp(self, country_dial_code: str, phone_number: str) -> None:
        raise NotImplementedError
    
    async def verify_otp(self, country_dial_code: str, phone_number: str, otp: str) -> bool:
        raise NotImplementedError


class UserAccountsServiceProvider(IUserAccountsService):

    def __init__(self):
        pass

    async def is_phone_number_registered(self, country_dial_code: str, phone_number: str) -> bool:
        raise NotImplementedError
    
    async def create_user_with_phone_number(
        self, country_dial_code: str, phone_number: str
    ) -> LuxtjUser:
        raise NotImplementedError
    
    async def get_user_by_phone_number(
        self, country_dial_code: str, phone_number: str
    ) -> LuxtjUser:
        raise NotImplementedError
    
    async def login_user_by_guid(self, guid: str) -> LuxtjUserAuthorizationDetail:
        raise NotImplementedError
