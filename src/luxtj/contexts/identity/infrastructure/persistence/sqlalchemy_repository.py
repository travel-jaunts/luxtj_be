from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.identity.domain.enums import UserTypeEnum
from luxtj.contexts.identity.domain.permission import Permission
from luxtj.contexts.identity.domain.role import Role
from luxtj.contexts.identity.domain.user import User
from luxtj.contexts.identity.infrastructure.persistence.sqlalchemy_models import (
    PermissionRow,
    RolePermissionRow,
    RoleRow,
    UserRow,
)
from luxtj.shared_kernel.application.pagination import PaginationMeta


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        row = UserRow(
            id=str(user.id),
            email=user.email,
            password_hash=user.password_hash,
            user_type=user.user_type.value,
            status=user.status.value,
            full_name=user.full_name,
            phone=user.phone,
            role_id=str(user.role_id) if user.role_id else None,
            password_reset_token_hash=user.password_reset_token_hash,
            password_reset_expires_at=user.password_reset_expires_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(row)
        await self._session.flush()

    async def save(self, user: User) -> None:
        row = await self._session.get(UserRow, str(user.id))
        if row is None:
            await self.add(user)
            return
        row.apply_domain(user)
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, str(user_id))
        return row.to_domain() if row else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.email == email.strip().lower())
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def get_by_password_reset_token_hash(self, token_hash: str) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.password_reset_token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def list_admin_users(
        self, *, page: int, page_size: int
    ) -> tuple[list[User], PaginationMeta]:
        filters = UserRow.user_type == UserTypeEnum.ADMIN.value
        total = await self._session.scalar(
            select(func.count()).select_from(UserRow).where(filters)
        )
        result = await self._session.execute(
            select(UserRow)
            .where(filters)
            .order_by(UserRow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [row.to_domain() for row in result.scalars().all()]
        return items, PaginationMeta(total=int(total or 0), page=page, size=page_size)

    async def count_by_role_id(self, role_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count()).select_from(UserRow).where(UserRow.role_id == str(role_id))
        )
        return int(total or 0)


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, role: Role) -> None:
        row = RoleRow(
            id=str(role.id),
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
        row.permissions = [
            RolePermissionRow(
                id=str(uuid4()),
                role_id=str(role.id),
                permission_code=code,
            )
            for code in sorted(role.permission_codes)
        ]
        self._session.add(row)
        await self._session.flush()

    async def save(self, role: Role) -> None:
        result = await self._session.execute(
            select(RoleRow).where(RoleRow.id == str(role.id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            await self.add(role)
            return
        row.name = role.name
        row.description = role.description
        row.is_active = role.is_active
        row.updated_at = role.updated_at
        row.permissions.clear()
        await self._session.flush()
        for code in sorted(role.permission_codes):
            row.permissions.append(
                RolePermissionRow(
                    id=str(uuid4()),
                    role_id=str(role.id),
                    permission_code=code,
                )
            )
        await self._session.flush()

    async def get_by_id(self, role_id: UUID) -> Role | None:
        result = await self._session.execute(
            select(RoleRow).where(RoleRow.id == str(role_id))
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def get_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(
            select(RoleRow).where(RoleRow.name == name.strip())
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def list_roles(
        self, *, page: int, page_size: int
    ) -> tuple[list[Role], PaginationMeta]:
        total = await self._session.scalar(select(func.count()).select_from(RoleRow))
        result = await self._session.execute(
            select(RoleRow)
            .order_by(RoleRow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [row.to_domain() for row in result.scalars().all()]
        return items, PaginationMeta(total=int(total or 0), page=page, size=page_size)


class SqlAlchemyPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, permissions: list[Permission]) -> None:
        if not permissions:
            return
        # ON CONFLICT so multi-worker boot (PM2) does not race on identity_permissions.code
        stmt = insert(PermissionRow).values(
            [
                {
                    "id": str(permission.id),
                    "code": permission.code,
                    "name": permission.name,
                    "description": permission.description,
                    "resource": permission.resource,
                    "action": permission.action,
                    "created_at": permission.created_at,
                }
                for permission in permissions
            ]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[PermissionRow.code],
            set_={
                "name": stmt.excluded.name,
                "description": stmt.excluded.description,
                "resource": stmt.excluded.resource,
                "action": stmt.excluded.action,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_all(self) -> list[Permission]:
        result = await self._session.execute(
            select(PermissionRow).order_by(PermissionRow.code.asc())
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_by_codes(self, codes: set[str]) -> list[Permission]:
        if not codes:
            return []
        result = await self._session.execute(
            select(PermissionRow).where(PermissionRow.code.in_(sorted(codes)))
        )
        return [row.to_domain() for row in result.scalars().all()]
