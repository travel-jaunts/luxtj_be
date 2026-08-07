from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from luxtj.contexts.identity.application.commands import (
    CreateAdminUserCommand,
    CreateRoleCommand,
    ForgotPasswordCommand,
    LoginCommand,
    RefreshCommand,
    RegisterB2CCommand,
    RegisterPartnerCommand,
    ResetPasswordCommand,
    UpdateAdminUserCommand,
    UpdateRoleCommand,
)
from luxtj.contexts.identity.application.use_cases import (
    AdminUserService,
    IdentityAuthService,
    RoleService,
)
from luxtj.contexts.identity.bootstrap import (
    build_admin_user_service,
    build_identity_auth_service,
    build_role_service,
)
from luxtj.contexts.identity.domain.enums import UserTypeEnum
from luxtj.contexts.identity.domain.errors import (
    AuthenticationError,
    ConflictError,
    IdentityError,
    NotFoundError,
    ValidationError,
)
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    RequireAdminPortal,
    get_current_principal,
    require_any_permission,
    require_permission,
)
from luxtj.contexts.identity.presentation.http.schemas import (
    CreateAdminUserBody,
    CreateRoleBody,
    ForgotPasswordBody,
    ForgotPasswordResponse,
    LoginBody,
    MeResponse,
    PermissionSerializer,
    RefreshBody,
    RegisterBody,
    ResetPasswordBody,
    RoleSummarySerializer,
    TokenResponse,
    UpdateAdminUserBody,
    UpdateRoleBody,
    UserSerializer,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiSuccessResponse,
    PaginatedResult,
    RequestProcessStatus,
)

public_auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_identity_router = APIRouter(tags=["admin_identity"])


def _http_error(exc: IdentityError) -> HTTPException:
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=401, detail=exc.message)
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=exc.message)
    if isinstance(exc, ValidationError):
        return HTTPException(status_code=422, detail=exc.message)
    return HTTPException(status_code=400, detail=exc.message)


# ── Public auth (Partner / B2C / shared login) ────────────────────────────────


@public_auth_router.post("/register/partner", response_model=ApiSuccessResponse[TokenResponse])
async def register_partner(
    body: Annotated[RegisterBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[TokenResponse]:
    try:
        result = await service.register_partner(
            RegisterPartnerCommand(
                email=body.email,
                password=body.password,
                full_name=body.full_name,
                phone=body.phone,
            )
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=TokenResponse.from_result(result))


@public_auth_router.post("/register/b2c", response_model=ApiSuccessResponse[TokenResponse])
async def register_b2c(
    body: Annotated[RegisterBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[TokenResponse]:
    try:
        result = await service.register_b2c(
            RegisterB2CCommand(
                email=body.email,
                password=body.password,
                full_name=body.full_name,
                phone=body.phone,
            )
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=TokenResponse.from_result(result))


@public_auth_router.post("/login", response_model=ApiSuccessResponse[TokenResponse])
async def login(
    body: Annotated[LoginBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[TokenResponse]:
    try:
        result = await service.login(LoginCommand(email=body.email, password=body.password))
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=TokenResponse.from_result(result))


@public_auth_router.post("/refresh", response_model=ApiSuccessResponse[TokenResponse])
async def refresh(
    body: Annotated[RefreshBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[TokenResponse]:
    try:
        result = await service.refresh(RefreshCommand(refresh_token=body.refresh_token))
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=TokenResponse.from_result(result))


@public_auth_router.post(
    "/forgot-password",
    response_model=ApiSuccessResponse[ForgotPasswordResponse],
)
async def forgot_password(
    body: Annotated[ForgotPasswordBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[ForgotPasswordResponse]:
    try:
        result = await service.forgot_password(ForgotPasswordCommand(email=body.email))
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(
        output=ForgotPasswordResponse(message=result.message, reset_token=result.reset_token)
    )


@public_auth_router.post("/reset-password", response_model=ApiSuccessResponse[dict])
async def reset_password(
    body: Annotated[ResetPasswordBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[dict]:
    try:
        await service.reset_password(
            ResetPasswordCommand(token=body.token, new_password=body.new_password)
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output={"message": "Password updated"})


@public_auth_router.post("/me", response_model=ApiSuccessResponse[MeResponse])
async def me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[MeResponse]:
    try:
        result = await service.me(principal.user_id)
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=MeResponse.from_result(result))


# ── Admin portal auth ─────────────────────────────────────────────────────────


@admin_identity_router.post("/auth/login", response_model=ApiSuccessResponse[TokenResponse])
async def admin_login(
    body: Annotated[LoginBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[TokenResponse]:
    try:
        result = await service.login(
            LoginCommand(
                email=body.email,
                password=body.password,
                allowed_user_types=frozenset(
                    {UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN}
                ),
            )
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=TokenResponse.from_result(result))


@admin_identity_router.post("/auth/refresh", response_model=ApiSuccessResponse[TokenResponse])
async def admin_refresh(
    body: Annotated[RefreshBody, Body(...)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[TokenResponse]:
    try:
        result = await service.refresh(
            RefreshCommand(
                refresh_token=body.refresh_token,
                allowed_user_types=frozenset(
                    {UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN}
                ),
            )
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=TokenResponse.from_result(result))


@admin_identity_router.post("/auth/me", response_model=ApiSuccessResponse[MeResponse])
async def admin_me(
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireAdminPortal)],
    service: Annotated[IdentityAuthService, Depends(build_identity_auth_service)],
) -> ApiSuccessResponse[MeResponse]:
    try:
        result = await service.me(principal.user_id)
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=MeResponse.from_result(result))


# ── Roles ─────────────────────────────────────────────────────────────────────


@admin_identity_router.post(
    "/roles/list",
    response_model=ApiSuccessResponse[PaginatedResult[RoleSummarySerializer]],
)
async def list_roles(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("roles.list"))],
    service: Annotated[RoleService, Depends(build_role_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
) -> ApiSuccessResponse[PaginatedResult[RoleSummarySerializer]]:
    items, meta = await service.list_roles(page=page, page_size=size)
    return ApiSuccessResponse(
        output=PaginatedResult(
            total=meta.total,
            page=meta.page,
            size=meta.size,
            items=[RoleSummarySerializer.from_domain(item) for item in items],
        )
    )


@admin_identity_router.post(
    "/roles/{role_id}/view",
    response_model=ApiSuccessResponse[RoleSummarySerializer],
)
async def view_role(
    role_id: UUID,
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("roles.view"))],
    service: Annotated[RoleService, Depends(build_role_service)],
) -> ApiSuccessResponse[RoleSummarySerializer]:
    try:
        role = await service.get_role(role_id)
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=RoleSummarySerializer.from_domain(role))


@admin_identity_router.post(
    "/roles/create",
    response_model=ApiSuccessResponse[RoleSummarySerializer],
)
async def create_role(
    body: Annotated[CreateRoleBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("roles.create"))],
    service: Annotated[RoleService, Depends(build_role_service)],
) -> ApiSuccessResponse[RoleSummarySerializer]:
    try:
        role = await service.create_role(
            CreateRoleCommand(
                name=body.name,
                description=body.description,
                permission_codes=frozenset(body.permission_codes),
                is_active=body.is_active,
            )
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=RoleSummarySerializer.from_domain(role))


@admin_identity_router.post(
    "/roles/{role_id}/edit",
    response_model=ApiSuccessResponse[RoleSummarySerializer],
)
async def edit_role(
    role_id: UUID,
    body: Annotated[UpdateRoleBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("roles.edit"))],
    service: Annotated[RoleService, Depends(build_role_service)],
) -> ApiSuccessResponse[RoleSummarySerializer]:
    try:
        role = await service.update_role(
            UpdateRoleCommand(
                role_id=role_id,
                name=body.name,
                description=body.description,
                permission_codes=(
                    frozenset(body.permission_codes)
                    if body.permission_codes is not None
                    else None
                ),
                is_active=body.is_active,
            )
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=RoleSummarySerializer.from_domain(role))


@admin_identity_router.post(
    "/permissions/list",
    response_model=ApiSuccessResponse[list[PermissionSerializer]],
)
async def list_permissions(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(
            require_any_permission(
                "roles.list",
                "roles.view",
                "roles.create",
                "roles.edit",
            )
        ),
    ],
    service: Annotated[RoleService, Depends(build_role_service)],
) -> ApiSuccessResponse[list[PermissionSerializer]]:
    items = await service.list_permissions()
    return ApiSuccessResponse(
        output=[PermissionSerializer.from_domain(item) for item in items]
    )


# ── Staff users ───────────────────────────────────────────────────────────────


@admin_identity_router.post(
    "/admin-users/list",
    response_model=ApiSuccessResponse[PaginatedResult[UserSerializer]],
)
async def list_admin_users(
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("admin_users.list"))
    ],
    service: Annotated[AdminUserService, Depends(build_admin_user_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
) -> ApiSuccessResponse[PaginatedResult[UserSerializer]]:
    items, meta = await service.list_users(page=page, page_size=size)
    return ApiSuccessResponse(
        output=PaginatedResult(
            total=meta.total,
            page=meta.page,
            size=meta.size,
            items=[UserSerializer.from_domain(item) for item in items],
        )
    )


@admin_identity_router.post(
    "/admin-users/{user_id}/view",
    response_model=ApiSuccessResponse[UserSerializer],
)
async def view_admin_user(
    user_id: UUID,
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("admin_users.view"))
    ],
    service: Annotated[AdminUserService, Depends(build_admin_user_service)],
) -> ApiSuccessResponse[UserSerializer]:
    try:
        user = await service.get_user(user_id)
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=UserSerializer.from_domain(user))


@admin_identity_router.post(
    "/admin-users/create",
    response_model=ApiSuccessResponse[UserSerializer],
)
async def create_admin_user(
    body: Annotated[CreateAdminUserBody, Body(...)],
    principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("admin_users.create"))
    ],
    service: Annotated[AdminUserService, Depends(build_admin_user_service)],
) -> ApiSuccessResponse[UserSerializer]:
    if body.as_superadmin:
        raise HTTPException(
            status_code=422,
            detail="Superadmin accounts cannot be created from staff users",
        )
    if body.role_id is None:
        raise HTTPException(status_code=422, detail="role_id is required for staff users")
    try:
        user = await service.create_user(
            CreateAdminUserCommand(
                email=body.email,
                password=body.password,
                full_name=body.full_name,
                role_id=body.role_id,
                phone=body.phone,
                as_superadmin=False,
            ),
            actor_is_superadmin=principal.is_superadmin,
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=UserSerializer.from_domain(user))


@admin_identity_router.post(
    "/admin-users/{user_id}/edit",
    response_model=ApiSuccessResponse[UserSerializer],
)
async def edit_admin_user(
    user_id: UUID,
    body: Annotated[UpdateAdminUserBody, Body(...)],
    principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("admin_users.edit"))
    ],
    service: Annotated[AdminUserService, Depends(build_admin_user_service)],
) -> ApiSuccessResponse[UserSerializer]:
    try:
        user = await service.update_user(
            UpdateAdminUserCommand(
                user_id=user_id,
                full_name=body.full_name,
                phone=body.phone,
                role_id=body.role_id,
                status=body.status,
                password=body.password,
            ),
            actor_is_superadmin=principal.is_superadmin,
        )
    except IdentityError as exc:
        raise _http_error(exc) from exc
    return ApiSuccessResponse(output=UserSerializer.from_domain(user))
