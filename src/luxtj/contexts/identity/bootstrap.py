from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.bootstrap import config
from luxtj.contexts.identity.application.password import PasswordHasher, TokenHasher
from luxtj.contexts.identity.application.ports import Clock
from luxtj.contexts.identity.application.use_cases import (
    AdminUserService,
    IdentityAuthService,
    IdentityBootstrapService,
    RoleService,
)
from luxtj.contexts.identity.infrastructure.auth.jwt import JoseIdentityTokenIssuer
from luxtj.contexts.identity.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle
from luxtj.utils import timeutils


class UtcClock(Clock):
    def utcnow(self) -> datetime:
        return timeutils.datetime_now()


def build_clock() -> Clock:
    return UtcClock()


def build_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def build_token_hasher() -> TokenHasher:
    return TokenHasher()


def build_token_issuer() -> JoseIdentityTokenIssuer:
    return JoseIdentityTokenIssuer(
        secret=config.AUTH_JWT_SECRET,
        algorithm=config.AUTH_JWT_ALGORITHM,
        access_ttl_seconds=config.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds=config.AUTH_REFRESH_TOKEN_TTL_SECONDS,
    )


def build_user_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def build_role_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> SqlAlchemyRoleRepository:
    return SqlAlchemyRoleRepository(session)


def build_permission_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> SqlAlchemyPermissionRepository:
    return SqlAlchemyPermissionRepository(session)


def build_identity_auth_service(
    user_repository: Annotated[SqlAlchemyUserRepository, Depends(build_user_repository)],
    role_repository: Annotated[SqlAlchemyRoleRepository, Depends(build_role_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(build_password_hasher)],
    token_hasher: Annotated[TokenHasher, Depends(build_token_hasher)],
    token_issuer: Annotated[JoseIdentityTokenIssuer, Depends(build_token_issuer)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> IdentityAuthService:
    return IdentityAuthService(
        user_repository=user_repository,
        role_repository=role_repository,
        password_hasher=password_hasher,
        token_hasher=token_hasher,
        token_issuer=token_issuer,
        clock=clock,
        password_reset_ttl_seconds=config.AUTH_PASSWORD_RESET_TTL_SECONDS,
        expose_reset_token=config.ENVIRONMENT == "development",
    )


def build_role_service(
    role_repository: Annotated[SqlAlchemyRoleRepository, Depends(build_role_repository)],
    permission_repository: Annotated[
        SqlAlchemyPermissionRepository, Depends(build_permission_repository)
    ],
    user_repository: Annotated[SqlAlchemyUserRepository, Depends(build_user_repository)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RoleService:
    return RoleService(
        role_repository=role_repository,
        permission_repository=permission_repository,
        user_repository=user_repository,
        clock=clock,
    )


def build_admin_user_service(
    user_repository: Annotated[SqlAlchemyUserRepository, Depends(build_user_repository)],
    role_repository: Annotated[SqlAlchemyRoleRepository, Depends(build_role_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(build_password_hasher)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> AdminUserService:
    return AdminUserService(
        user_repository=user_repository,
        role_repository=role_repository,
        password_hasher=password_hasher,
        clock=clock,
    )


def build_identity_bootstrap_service(
    session: AsyncSession,
) -> IdentityBootstrapService:
    return IdentityBootstrapService(
        permission_repository=SqlAlchemyPermissionRepository(session),
        user_repository=SqlAlchemyUserRepository(session),
        password_hasher=PasswordHasher(),
        clock=UtcClock(),
    )
