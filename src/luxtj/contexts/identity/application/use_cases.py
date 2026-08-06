from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from luxtj.contexts.identity.application.commands import (
    CreateAdminUserCommand,
    CreateRoleCommand,
    ForgotPasswordCommand,
    LoginCommand,
    RegisterB2CCommand,
    RegisterPartnerCommand,
    ResetPasswordCommand,
    UpdateAdminUserCommand,
    UpdateRoleCommand,
)
from luxtj.contexts.identity.application.password import PasswordHasher, TokenHasher
from luxtj.contexts.identity.application.permissions_catalog import (
    PERMISSION_DEFINITIONS,
    all_permission_codes,
)
from luxtj.contexts.identity.application.ports import (
    Clock,
    IdentityTokenIssuer,
    PermissionRepository,
    RoleRepository,
    UserRepository,
)
from luxtj.contexts.identity.domain.enums import UserStatusEnum, UserTypeEnum
from luxtj.contexts.identity.domain.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from luxtj.contexts.identity.domain.permission import Permission
from luxtj.contexts.identity.domain.role import Role
from luxtj.contexts.identity.domain.user import User
from luxtj.shared_kernel.application.pagination import PaginationMeta


@dataclass(frozen=True)
class AuthTokenResult:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    token_type: str = "Bearer"


@dataclass(frozen=True)
class ForgotPasswordResult:
    message: str
    reset_token: str | None = None  # only returned in development for local testing


@dataclass(frozen=True)
class UserProfileResult:
    user: User
    role: Role | None
    permissions: list[str]


class IdentityAuthService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        password_hasher: PasswordHasher,
        token_hasher: TokenHasher,
        token_issuer: IdentityTokenIssuer,
        clock: Clock,
        password_reset_ttl_seconds: int = 3600,
        expose_reset_token: bool = False,
    ) -> None:
        self._users = user_repository
        self._roles = role_repository
        self._passwords = password_hasher
        self._token_hasher = token_hasher
        self._tokens = token_issuer
        self._clock = clock
        self._password_reset_ttl_seconds = password_reset_ttl_seconds
        self._expose_reset_token = expose_reset_token

    async def register_partner(self, command: RegisterPartnerCommand) -> AuthTokenResult:
        return await self._register(
            email=command.email,
            password=command.password,
            full_name=command.full_name,
            phone=command.phone,
            user_type=UserTypeEnum.PARTNER,
        )

    async def register_b2c(self, command: RegisterB2CCommand) -> AuthTokenResult:
        return await self._register(
            email=command.email,
            password=command.password,
            full_name=command.full_name,
            phone=command.phone,
            user_type=UserTypeEnum.B2C,
        )

    async def login(self, command: LoginCommand) -> AuthTokenResult:
        email = command.email.strip().lower()
        user = await self._users.get_by_email(email)
        if user is None or not self._passwords.verify(command.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active():
            raise AuthenticationError("User account is not active")
        if command.allowed_user_types and user.user_type not in command.allowed_user_types:
            raise AuthenticationError("User type is not allowed for this login endpoint")
        return await self._issue_for_user(user)

    async def forgot_password(self, command: ForgotPasswordCommand) -> ForgotPasswordResult:
        email = command.email.strip().lower()
        user = await self._users.get_by_email(email)
        # Always return success message to avoid email enumeration
        message = "If the email exists, a password reset token has been issued"
        if user is None or not user.is_active():
            return ForgotPasswordResult(message=message)

        raw_token = self._token_hasher.generate_raw_token()
        now = self._clock.utcnow()
        user.set_password_reset(
            token_hash=self._token_hasher.hash(raw_token),
            expires_at=now + timedelta(seconds=self._password_reset_ttl_seconds),
            now=now,
        )
        await self._users.save(user)
        return ForgotPasswordResult(
            message=message,
            reset_token=raw_token if self._expose_reset_token else None,
        )

    async def reset_password(self, command: ResetPasswordCommand) -> None:
        if len(command.new_password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        token_hash = self._token_hasher.hash(command.token)
        user = await self._users.get_by_password_reset_token_hash(token_hash)
        if user is None:
            raise ValidationError("Invalid or expired reset token")
        now = self._clock.utcnow()
        if (
            user.password_reset_expires_at is None
            or user.password_reset_expires_at < now
        ):
            raise ValidationError("Invalid or expired reset token")
        user.set_password(self._passwords.hash(command.new_password), now=now)
        await self._users.save(user)

    async def me(self, user_id: UUID) -> UserProfileResult:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        role = None
        permissions: list[str] = []
        if user.user_type == UserTypeEnum.SUPERADMIN:
            permissions = sorted(all_permission_codes())
        elif user.role_id is not None:
            role = await self._roles.get_by_id(user.role_id)
            if role is not None:
                permissions = sorted(role.permission_codes)
        return UserProfileResult(user=user, role=role, permissions=permissions)

    async def _register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone: str | None,
        user_type: UserTypeEnum,
    ) -> AuthTokenResult:
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        normalized = email.strip().lower()
        existing = await self._users.get_by_email(normalized)
        if existing is not None:
            raise ConflictError("Email is already registered")
        now = self._clock.utcnow()
        user = User.create(
            email=normalized,
            password_hash=self._passwords.hash(password),
            user_type=user_type,
            full_name=full_name,
            phone=phone,
            now=now,
        )
        await self._users.add(user)
        return await self._issue_for_user(user)

    async def _issue_for_user(self, user: User) -> AuthTokenResult:
        permissions: list[str] = []
        if user.user_type == UserTypeEnum.SUPERADMIN:
            permissions = ["*"]
        elif user.user_type == UserTypeEnum.ADMIN:
            if user.role_id is None:
                raise AuthenticationError("Admin user has no role assigned")
            role = await self._roles.get_by_id(user.role_id)
            if role is None or not role.is_active:
                raise AuthenticationError("Admin role is missing or inactive")
            permissions = sorted(role.permission_codes)

        access, refresh, access_ttl, refresh_ttl = await self._tokens.issue_pair(
            user=user,
            permission_codes=permissions,
        )
        return AuthTokenResult(
            access_token=access,
            refresh_token=refresh,
            expires_in=access_ttl,
            refresh_expires_in=refresh_ttl,
        )


class RoleService:
    def __init__(
        self,
        *,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        user_repository: UserRepository,
        clock: Clock,
    ) -> None:
        self._roles = role_repository
        self._permissions = permission_repository
        self._users = user_repository
        self._clock = clock

    async def list_roles(
        self, *, page: int, page_size: int
    ) -> tuple[list[Role], PaginationMeta]:
        return await self._roles.list_roles(page=page, page_size=page_size)

    async def get_role(self, role_id: UUID) -> Role:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise NotFoundError("Role not found")
        return role

    async def create_role(self, command: CreateRoleCommand) -> Role:
        await self._assert_permission_codes(set(command.permission_codes))
        existing = await self._roles.get_by_name(command.name.strip())
        if existing is not None:
            raise ConflictError("Role name already exists")
        role = Role.create(
            name=command.name,
            description=command.description,
            permission_codes=set(command.permission_codes),
            is_active=command.is_active,
            now=self._clock.utcnow(),
        )
        await self._roles.add(role)
        return role

    async def update_role(self, command: UpdateRoleCommand) -> Role:
        role = await self._roles.get_by_id(command.role_id)
        if role is None:
            raise NotFoundError("Role not found")
        if command.permission_codes is not None:
            await self._assert_permission_codes(set(command.permission_codes))
        if command.name is not None:
            other = await self._roles.get_by_name(command.name.strip())
            if other is not None and other.id != role.id:
                raise ConflictError("Role name already exists")
        role.update(
            name=command.name,
            description=command.description,
            is_active=command.is_active,
            permission_codes=(
                set(command.permission_codes) if command.permission_codes is not None else None
            ),
            now=self._clock.utcnow(),
        )
        await self._roles.save(role)
        return role

    async def list_permissions(self) -> list[Permission]:
        return await self._permissions.list_all()

    async def _assert_permission_codes(self, codes: set[str]) -> None:
        known = all_permission_codes()
        unknown = codes - known
        if unknown:
            raise ValidationError(f"Unknown permission codes: {', '.join(sorted(unknown))}")


class AdminUserService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._users = user_repository
        self._roles = role_repository
        self._passwords = password_hasher
        self._clock = clock

    async def list_users(
        self, *, page: int, page_size: int
    ) -> tuple[list[User], PaginationMeta]:
        return await self._users.list_admin_users(page=page, page_size=page_size)

    async def get_user(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None or user.user_type not in {
            UserTypeEnum.ADMIN,
            UserTypeEnum.SUPERADMIN,
        }:
            raise NotFoundError("Admin user not found")
        return user

    async def create_user(
        self,
        command: CreateAdminUserCommand,
        *,
        actor_is_superadmin: bool,
    ) -> User:
        if command.as_superadmin and not actor_is_superadmin:
            raise ValidationError("Only a superadmin can create another superadmin")
        if len(command.password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        email = command.email.strip().lower()
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("Email is already registered")

        role_id: UUID | None = None
        user_type = UserTypeEnum.SUPERADMIN if command.as_superadmin else UserTypeEnum.ADMIN
        if not command.as_superadmin:
            if command.role_id is None:
                raise ValidationError("role_id is required for admin users")
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError("Role not found")
            if not role.is_active:
                raise ValidationError("Cannot assign an inactive role")
            role_id = role.id

        user = User.create(
            email=email,
            password_hash=self._passwords.hash(command.password),
            user_type=user_type,
            full_name=command.full_name,
            phone=command.phone,
            role_id=role_id,
            now=self._clock.utcnow(),
        )
        await self._users.add(user)
        return user

    async def update_user(
        self,
        command: UpdateAdminUserCommand,
        *,
        actor_is_superadmin: bool,
    ) -> User:
        user = await self.get_user(command.user_id)
        if user.user_type == UserTypeEnum.SUPERADMIN and not actor_is_superadmin:
            raise ValidationError("Only a superadmin can edit another superadmin")

        if command.role_id is not None:
            if user.user_type != UserTypeEnum.ADMIN:
                raise ValidationError("Cannot assign a role to a superadmin")
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError("Role not found")
            if not role.is_active:
                raise ValidationError("Cannot assign an inactive role")
            user.assign_role(command.role_id, now=self._clock.utcnow())

        user.update_profile(
            full_name=command.full_name,
            phone=command.phone,
            status=command.status,
            now=self._clock.utcnow(),
        )
        if command.password is not None:
            if len(command.password) < 8:
                raise ValidationError("Password must be at least 8 characters")
            user.set_password(self._passwords.hash(command.password), now=self._clock.utcnow())

        await self._users.save(user)
        return user


class IdentityBootstrapService:
    """Seeds fixed permissions and optional initial superadmin."""

    def __init__(
        self,
        *,
        permission_repository: PermissionRepository,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._permissions = permission_repository
        self._users = user_repository
        self._passwords = password_hasher
        self._clock = clock

    async def seed_permissions(self) -> None:
        now = self._clock.utcnow()
        items = [
            Permission(
                id=uuid4(),
                code=item.code,
                name=item.name,
                description=item.description,
                resource=item.resource,
                action=item.action,
                created_at=now,
            )
            for item in PERMISSION_DEFINITIONS
        ]
        await self._permissions.upsert_many(items)

    async def ensure_superadmin(self, *, email: str, password: str, full_name: str) -> None:
        if not email or not password:
            return
        existing = await self._users.get_by_email(email.strip().lower())
        if existing is not None:
            return
        user = User.create(
            email=email,
            password_hash=self._passwords.hash(password),
            user_type=UserTypeEnum.SUPERADMIN,
            full_name=full_name or "Super Admin",
            now=self._clock.utcnow(),
        )
        await self._users.add(user)
