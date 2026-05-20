from typing import Protocol

from luxtj.domain.entity import LuxtjUser, LuxtjUserAuthorizationDetail


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
