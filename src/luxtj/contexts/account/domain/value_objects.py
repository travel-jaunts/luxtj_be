from dataclasses import dataclass


@dataclass(frozen=True)
class PhoneIdentity:
    dial_code: str
    phone_number: str

    def __post_init__(self) -> None:
        dial_code = self.dial_code.strip()
        phone_number = self.phone_number.strip()

        if not dial_code:
            raise ValueError("dial_code is required")
        if not phone_number:
            raise ValueError("phone_number is required")

        object.__setattr__(self, "dial_code", dial_code)
        object.__setattr__(self, "phone_number", phone_number)

    @property
    def e164_like(self) -> str:
        return f"{self.dial_code}{self.phone_number}"
