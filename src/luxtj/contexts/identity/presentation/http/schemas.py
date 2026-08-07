from uuid import UUID

from pydantic import Field

from luxtj.contexts.identity.application.use_cases import AuthTokenResult, UserProfileResult
from luxtj.contexts.identity.domain.enums import UserStatusEnum, UserTypeEnum
from luxtj.contexts.identity.domain.permission import Permission
from luxtj.contexts.identity.domain.role import Role
from luxtj.contexts.identity.domain.user import User
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class RegisterBody(ApiSerializerBaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=256)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=32)


class LoginBody(ApiSerializerBaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=256)


class RefreshBody(ApiSerializerBaseModel):
    refresh_token: str = Field(..., min_length=1)


class ForgotPasswordBody(ApiSerializerBaseModel):
    email: str = Field(..., min_length=3, max_length=320)


class ResetPasswordBody(ApiSerializerBaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=256)


class TokenResponse(ApiSerializerBaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    token_type: str = "Bearer"

    @classmethod
    def from_result(cls, result: AuthTokenResult) -> "TokenResponse":
        return cls(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_in=result.expires_in,
            refresh_expires_in=result.refresh_expires_in,
            token_type=result.token_type,
        )


class ForgotPasswordResponse(ApiSerializerBaseModel):
    message: str
    reset_token: str | None = None


class RoleSummarySerializer(ApiSerializerBaseModel):
    id: str
    name: str
    description: str
    is_active: bool
    permission_codes: list[str]

    @classmethod
    def from_domain(cls, role: Role) -> "RoleSummarySerializer":
        return cls(
            id=str(role.id),
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permission_codes=sorted(role.permission_codes),
        )


class UserSerializer(ApiSerializerBaseModel):
    id: str
    email: str
    user_type: UserTypeEnum
    status: UserStatusEnum
    full_name: str
    phone: str | None
    role_id: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, user: User) -> "UserSerializer":
        return cls(
            id=str(user.id),
            email=user.email,
            user_type=user.user_type,
            status=user.status,
            full_name=user.full_name,
            phone=user.phone,
            role_id=str(user.role_id) if user.role_id else None,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )


class MeResponse(ApiSerializerBaseModel):
    user: UserSerializer
    role: RoleSummarySerializer | None
    permissions: list[str]

    @classmethod
    def from_result(cls, result: UserProfileResult) -> "MeResponse":
        return cls(
            user=UserSerializer.from_domain(result.user),
            role=RoleSummarySerializer.from_domain(result.role) if result.role else None,
            permissions=result.permissions,
        )


class PermissionSerializer(ApiSerializerBaseModel):
    code: str
    name: str
    description: str
    resource: str
    action: str

    @classmethod
    def from_domain(cls, permission: Permission) -> "PermissionSerializer":
        return cls(
            code=permission.code,
            name=permission.name,
            description=permission.description,
            resource=permission.resource,
            action=permission.action,
        )


class CreateRoleBody(ApiSerializerBaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field("", max_length=2000)
    permission_codes: list[str] = Field(..., min_length=1)
    is_active: bool = True


class UpdateRoleBody(ApiSerializerBaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=2000)
    permission_codes: list[str] | None = Field(None, min_length=1)
    is_active: bool | None = None


class CreateAdminUserBody(ApiSerializerBaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=256)
    full_name: str = Field(..., min_length=1, max_length=255)
    role_id: UUID | None = None
    phone: str | None = Field(None, max_length=32)
    as_superadmin: bool = False


class UpdateAdminUserBody(ApiSerializerBaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=32)
    role_id: UUID | None = None
    status: UserStatusEnum | None = None
    password: str | None = Field(None, min_length=8, max_length=256)
