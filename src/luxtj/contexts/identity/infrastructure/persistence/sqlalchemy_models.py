from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from luxtj.contexts.identity.domain.enums import UserStatusEnum, UserTypeEnum
from luxtj.contexts.identity.domain.permission import Permission
from luxtj.contexts.identity.domain.role import Role
from luxtj.contexts.identity.domain.user import User
from luxtj.shared_kernel.application.pagination import PaginationMeta


class IdentityBase(DeclarativeBase):
    pass


class PermissionRow(IdentityBase):
    __tablename__ = "identity_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    resource: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> Permission:
        return Permission(
            id=UUID(self.id),
            code=self.code,
            name=self.name,
            description=self.description,
            resource=self.resource,
            action=self.action,
            created_at=self.created_at,
        )


class RoleRow(IdentityBase):
    __tablename__ = "identity_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    permissions: Mapped[list["RolePermissionRow"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_domain(self) -> Role:
        return Role(
            id=UUID(self.id),
            name=self.name,
            description=self.description,
            is_active=self.is_active,
            permission_codes={rp.permission_code for rp in self.permissions},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class RolePermissionRow(IdentityBase):
    __tablename__ = "identity_role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("identity_roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_code: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("identity_permissions.code", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[RoleRow] = relationship(back_populates="permissions")


class UserRow(IdentityBase):
    __tablename__ = "identity_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    user_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("identity_roles.id", ondelete="SET NULL"), nullable=True
    )
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> User:
        return User(
            id=UUID(self.id),
            email=self.email,
            password_hash=self.password_hash,
            user_type=UserTypeEnum(self.user_type),
            status=UserStatusEnum(self.status),
            full_name=self.full_name,
            phone=self.phone,
            role_id=UUID(self.role_id) if self.role_id else None,
            password_reset_token_hash=self.password_reset_token_hash,
            password_reset_expires_at=self.password_reset_expires_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def apply_domain(self, user: User) -> None:
        self.email = user.email
        self.password_hash = user.password_hash
        self.user_type = user.user_type.value
        self.status = user.status.value
        self.full_name = user.full_name
        self.phone = user.phone
        self.role_id = str(user.role_id) if user.role_id else None
        self.password_reset_token_hash = user.password_reset_token_hash
        self.password_reset_expires_at = user.password_reset_expires_at
        self.updated_at = user.updated_at
