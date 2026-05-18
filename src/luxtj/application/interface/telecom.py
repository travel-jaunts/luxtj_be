from typing import Protocol


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
