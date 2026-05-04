from typing import Protocol, Any

from luxtj.domain.entity import LuxtjUser, LuxtjUserAuthorizationDetail


class ILogger(Protocol):
    def info(self, message: str, extra: dict[str, Any] | None = None):
        """
        Log an info message
        """
        ...


class ITelecomService(Protocol):
    async def is_valid_phone_number(self, country_dial_code: str, phone_number: str) -> bool:
        """
        Check if the phone number is valid
        """
        ...

    async def send_otp(self, country_dial_code: str, phone_number: str) -> None:
        """
        Send OTP to the phone number
        """
        ...

    async def verify_otp(self, country_dial_code: str, phone_number: str, otp: str) -> bool:
        """
        Verify the OTP for the phone number
        """
        ...


class IUserAccountsService(Protocol):
    async def is_phone_number_registered(self, country_dial_code: str, phone_number: str) -> bool:
        """
        Check if the phone number is registered in repository
        """
        ...

    async def create_user_with_phone_number(
        self, country_dial_code: str, phone_number: str
    ) -> LuxtjUser:
        """
        Create a new user with the given country dial code and phone number
        """
        ...

    async def get_user_by_phone_number(
        self, country_dial_code: str, phone_number: str
    ) -> LuxtjUser:
        """
        Get user by the given country dial code and phone number
        """
        ...

    async def login_user_by_guid(self, guid: str) -> LuxtjUserAuthorizationDetail:
        """
        Login the user with the given guid
        """
        ...
