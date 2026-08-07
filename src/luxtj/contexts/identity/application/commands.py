from dataclasses import dataclass
from uuid import UUID

from luxtj.contexts.identity.domain.enums import UserStatusEnum, UserTypeEnum


@dataclass(frozen=True)
class RegisterPartnerCommand:
    email: str
    password: str
    full_name: str
    phone: str | None = None


@dataclass(frozen=True)
class RegisterB2CCommand:
    email: str
    password: str
    full_name: str
    phone: str | None = None


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str
    allowed_user_types: frozenset[UserTypeEnum] | None = None


@dataclass(frozen=True)
class ForgotPasswordCommand:
    email: str


@dataclass(frozen=True)
class ResetPasswordCommand:
    token: str
    new_password: str


@dataclass(frozen=True)
class RefreshCommand:
    refresh_token: str
    allowed_user_types: frozenset[UserTypeEnum] | None = None


@dataclass(frozen=True)
class CreateRoleCommand:
    name: str
    description: str
    permission_codes: frozenset[str]
    is_active: bool = True


@dataclass(frozen=True)
class UpdateRoleCommand:
    role_id: UUID
    name: str | None = None
    description: str | None = None
    permission_codes: frozenset[str] | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class CreateAdminUserCommand:
    email: str
    password: str
    full_name: str
    role_id: UUID | None = None
    phone: str | None = None
    as_superadmin: bool = False


@dataclass(frozen=True)
class UpdateAdminUserCommand:
    user_id: UUID
    full_name: str | None = None
    phone: str | None = None
    role_id: UUID | None = None
    status: UserStatusEnum | None = None
    password: str | None = None
