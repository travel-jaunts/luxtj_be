from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.contexts.identity.domain.enums import UserStatusEnum, UserTypeEnum
from luxtj.contexts.identity.domain.errors import ValidationError


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str
    user_type: UserTypeEnum
    status: UserStatusEnum
    full_name: str
    phone: str | None
    role_id: UUID | None
    password_reset_token_hash: str | None
    password_reset_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        email: str,
        password_hash: str,
        user_type: UserTypeEnum,
        full_name: str,
        now: datetime,
        phone: str | None = None,
        role_id: UUID | None = None,
        status: UserStatusEnum = UserStatusEnum.ACTIVE,
    ) -> User:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValidationError("Email is required")
        if user_type == UserTypeEnum.ADMIN and role_id is None:
            raise ValidationError("Admin users must be assigned a role")
        if user_type == UserTypeEnum.SUPERADMIN and role_id is not None:
            raise ValidationError("Superadmin must not have a role")
        if user_type in {UserTypeEnum.PARTNER, UserTypeEnum.B2C} and role_id is not None:
            raise ValidationError("Partner and B2C users must not have a role")

        return cls(
            id=uuid4(),
            email=normalized_email,
            password_hash=password_hash,
            user_type=user_type,
            status=status,
            full_name=full_name.strip(),
            phone=phone.strip() if phone and phone.strip() else None,
            role_id=role_id,
            password_reset_token_hash=None,
            password_reset_expires_at=None,
            created_at=now,
            updated_at=now,
        )

    def is_active(self) -> bool:
        return self.status == UserStatusEnum.ACTIVE

    def assign_role(self, role_id: UUID, *, now: datetime) -> None:
        if self.user_type != UserTypeEnum.ADMIN:
            raise ValidationError("Only admin users can be assigned a role")
        self.role_id = role_id
        self.updated_at = now

    def update_profile(
        self,
        *,
        full_name: str | None = None,
        phone: str | None = None,
        status: UserStatusEnum | None = None,
        now: datetime,
    ) -> None:
        if full_name is not None:
            self.full_name = full_name.strip()
        if phone is not None:
            self.phone = phone.strip() if phone.strip() else None
        if status is not None:
            self.status = status
        self.updated_at = now

    def set_password(self, password_hash: str, *, now: datetime) -> None:
        self.password_hash = password_hash
        self.password_reset_token_hash = None
        self.password_reset_expires_at = None
        self.updated_at = now

    def set_password_reset(
        self,
        *,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        self.password_reset_token_hash = token_hash
        self.password_reset_expires_at = expires_at
        self.updated_at = now

    def clear_password_reset(self, *, now: datetime) -> None:
        self.password_reset_token_hash = None
        self.password_reset_expires_at = None
        self.updated_at = now
