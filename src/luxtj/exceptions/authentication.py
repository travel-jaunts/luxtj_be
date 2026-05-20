from luxtj.exceptions.base import LuxtjDomainException


class LuxtjAuthenticationException(LuxtjDomainException):
    """
    Base exception for all authentication exceptions in luxtj
    """

    pass


class InvalidPhoneNumberException(LuxtjAuthenticationException):
    """
    Exception raised when the phone number is invalid
    """

    def __init__(self, country_dial_code: str, phone_number: str):
        self.country_dial_code = country_dial_code
        self.phone_number = phone_number
        super().__init__(f"Invalid phone number: {country_dial_code} {phone_number}")


class PhoneNumberAlreadyRegisteredException(LuxtjAuthenticationException):
    """
    Exception raised when the phone number is already registered
    """

    def __init__(self, country_dial_code: str, phone_number: str):
        self.country_dial_code = country_dial_code
        self.phone_number = phone_number
        super().__init__(f"Phone number already registered: {country_dial_code} {phone_number}")


class PhoneNumberNotRegisteredException(LuxtjAuthenticationException):
    """
    Exception raised when the phone number is not registered
    """

    def __init__(self, country_dial_code: str, phone_number: str):
        self.country_dial_code = country_dial_code
        self.phone_number = phone_number
        super().__init__(f"Phone number not registered: {country_dial_code} {phone_number}")
