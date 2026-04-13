from dataclasses import dataclass

from luxtj.domain.enums import CustomerStatusEnum, CustomerTierEnum


@dataclass
class UpdateUserDTO:
    first_name: str
    last_name: str
    phone_number: str
    email: str
    tier: CustomerTierEnum
    status: CustomerStatusEnum
