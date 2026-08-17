from enum import StrEnum


class AuthFlowType(StrEnum):
    SIGNUP = "signup"
    LOGIN = "login"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"
