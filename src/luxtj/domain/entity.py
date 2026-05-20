from dataclasses import dataclass


@dataclass
class UserContactDetail:
    country_dial_code: str
    phone_number: str
    email: str | None


@dataclass
class LuxtjUser:
    guid: str
    contact: UserContactDetail
    first_name: str | None
    last_name: str | None


@dataclass
class LuxtjUserAuthorizationDetail:
    access_token: str
    refresh_token: str
