from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.identity.domain.enums import UserTypeEnum
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_current_principal,
    require_permission,
)
from luxtj.contexts.integration.application.booking_api_logs import BookingApiLogsService
from luxtj.contexts.integration.application.commands import (
    UpdateBookingApiCommand,
    UpdateModuleStatusCommand,
    UpdateOtherApiCommand,
    UpdatePaymentGatewayCommand,
    UpdateSubModuleStatusCommand,
)
from luxtj.contexts.integration.application.use_cases import (
    IntegrationNotFoundError,
    IntegrationRegistryService,
    IntegrationValidationError,
)
from luxtj.contexts.integration.bootstrap import build_integration_registry_service
from luxtj.contexts.integration.presentation.http.schemas import (
    BookingApiSerializer,
    IntegrationsCurrencyOptionSerializer,
    IntegrationsOverviewSerializer,
    ModuleSerializer,
    OtherApiSerializer,
    PaymentGatewaySerializer,
    StatusBody,
    SubModuleSerializer,
    UpdateBookingApiBody,
    UpdateOtherApiBody,
    UpdatePaymentGatewayBody,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel, ApiSuccessResponse

integrations_router = APIRouter(prefix="/integrations", tags=["admin-integrations"])


class BookingApiLogsListBody(ApiSerializerBaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100, alias="pageSize")
    booking_api_id: str | None = Field(None, alias="bookingApiId")
    booking_api_code: str | None = Field(None, alias="bookingApiCode")
    sub_module: str | None = Field(None, alias="subModule")
    request_type: str | None = Field(None, alias="requestType")
    from_date: date | None = Field(None, alias="fromDate")
    to_date: date | None = Field(None, alias="toDate")


class BookingApiLogDownloadBody(ApiSerializerBaseModel):
    part: str = Field(..., pattern="^(request|response|headers)$")


def _logs_service(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> BookingApiLogsService:
    return BookingApiLogsService(session)


def _principal_can_view_api_logs(
    principal: AuthenticatedPrincipal, *, sub_module: str, api_code: str
) -> bool:
    from luxtj.contexts.integration.application.booking_api_logs import (
        permission_codes_for_api,
    )

    if principal.is_superadmin:
        return True
    for code in permission_codes_for_api(sub_module=sub_module, api_code=api_code):
        if principal.has_permission(code):
            return True
    return False


@integrations_router.post(
    "/booking-api-logs/list",
    response_model=ApiSuccessResponse[dict[str, Any]],
)
async def list_booking_api_logs(
    body: Annotated[BookingApiLogsListBody, Body(...)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    logs: Annotated[BookingApiLogsService, Depends(_logs_service)],
) -> ApiSuccessResponse[dict[str, Any]]:
    # Admin portal only (superadmin/admin). Permission scoped per booking API below.
    if principal.user_type not in (UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN):
        raise HTTPException(status_code=403, detail="User type is not allowed")

    resolved = await logs.resolve_booking_api(
        booking_api_id=body.booking_api_id,
        booking_api_code=body.booking_api_code,
        sub_module=body.sub_module,
    )
    if resolved is None:
        raise HTTPException(
            status_code=404,
            detail="Booking API not found — provide bookingApiId or bookingApiCode + subModule",
        )
    if not _principal_can_view_api_logs(
        principal, sub_module=resolved["subModule"], api_code=resolved["code"]
    ):
        raise HTTPException(status_code=403, detail="Missing permission for these API logs")

    data = await logs.list_logs(
        page=body.page,
        page_size=body.page_size,
        booking_api_id=resolved["id"],
        request_type=body.request_type,
        from_date=body.from_date,
        to_date=body.to_date,
    )
    return ApiSuccessResponse(output=data)


@integrations_router.post(
    "/booking-api-logs/{log_id}",
    response_model=ApiSuccessResponse[dict[str, Any]],
)
async def get_booking_api_log(
    log_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    logs: Annotated[BookingApiLogsService, Depends(_logs_service)],
) -> ApiSuccessResponse[dict[str, Any]]:
    if principal.user_type not in (UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN):
        raise HTTPException(status_code=403, detail="User type is not allowed")
    detail = await logs.get_log(log_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Log not found")
    sub = str(detail.get("subModule") or "")
    code = str(detail.get("bookingApiCode") or "")
    if (
        not sub
        or not code
        or not _principal_can_view_api_logs(principal, sub_module=sub, api_code=code)
    ):
        raise HTTPException(status_code=403, detail="Missing permission for these API logs")
    return ApiSuccessResponse(output=detail)


@integrations_router.post("/booking-api-logs/{log_id}/download")
async def download_booking_api_log_part(
    log_id: str,
    body: Annotated[BookingApiLogDownloadBody, Body(...)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    logs: Annotated[BookingApiLogsService, Depends(_logs_service)],
) -> Response:
    if principal.user_type not in (UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN):
        raise HTTPException(status_code=403, detail="User type is not allowed")
    detail = await logs.get_log(log_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Log not found")
    sub = str(detail.get("subModule") or "")
    code = str(detail.get("bookingApiCode") or "")
    if (
        not sub
        or not code
        or not _principal_can_view_api_logs(principal, sub_module=sub, api_code=code)
    ):
        raise HTTPException(status_code=403, detail="Missing permission for these API logs")

    part = body.part  # type: ignore[assignment]
    payload = await logs.download_part(log_id, part)  # type: ignore[arg-type]
    if payload is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return Response(
        content=payload["content"],
        media_type=payload["mediaType"],
        headers={
            "Content-Disposition": f'attachment; filename="{payload["filename"]}"',
            "X-Download-Filename": payload["filename"],
        },
    )


@integrations_router.post(
    "/overview",
    response_model=ApiSuccessResponse[IntegrationsOverviewSerializer],
)
async def integrations_overview(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[IntegrationsOverviewSerializer]:
    data = await service.list_overview()
    return ApiSuccessResponse(
        output=IntegrationsOverviewSerializer(
            modules=[ModuleSerializer.from_domain(m) for m in data["modules"]],
            sub_modules=[
                SubModuleSerializer.from_domain(item["entity"]) for item in data["subModules"]
            ],
            booking_apis=[BookingApiSerializer.from_overview(item) for item in data["bookingApis"]],
            payment_gateways=[
                PaymentGatewaySerializer.from_overview(item) for item in data["paymentGateways"]
            ],
            other_apis=[OtherApiSerializer.from_overview(item) for item in data["otherApis"]],
            currencies=[
                IntegrationsCurrencyOptionSerializer(
                    code=c["code"],
                    currency_name=c["currency_name"],
                    currency_symbol=c["currency_symbol"],
                    active=bool(c["active"]),
                )
                for c in data.get("currencies") or []
            ],
        )
    )


@integrations_router.post(
    "/sync-catalog",
    response_model=ApiSuccessResponse[dict],
)
async def sync_catalog(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.edit"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[dict]:
    await service.sync_catalog()
    return ApiSuccessResponse(output={"synced": True})


@integrations_router.post(
    "/modules/{module_id}/status",
    response_model=ApiSuccessResponse[ModuleSerializer],
)
async def update_module_status(
    module_id: UUID,
    body: Annotated[StatusBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.edit"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[ModuleSerializer]:
    try:
        module = await service.update_module_status(
            UpdateModuleStatusCommand(module_id=module_id, status=body.status)
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiSuccessResponse(output=ModuleSerializer.from_domain(module))


@integrations_router.post(
    "/sub-modules/{sub_module_id}/status",
    response_model=ApiSuccessResponse[SubModuleSerializer],
)
async def update_sub_module_status(
    sub_module_id: UUID,
    body: Annotated[StatusBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.edit"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[SubModuleSerializer]:
    try:
        sub = await service.update_sub_module_status(
            UpdateSubModuleStatusCommand(sub_module_id=sub_module_id, status=body.status)
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiSuccessResponse(output=SubModuleSerializer.from_domain(sub))


@integrations_router.post(
    "/booking-apis/{booking_api_id}/edit",
    response_model=ApiSuccessResponse[BookingApiSerializer],
)
async def update_booking_api(
    booking_api_id: UUID,
    body: Annotated[UpdateBookingApiBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.edit"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[BookingApiSerializer]:
    try:
        api = await service.update_booking_api(
            UpdateBookingApiCommand(
                booking_api_id=booking_api_id,
                status=body.status,
                api_type=body.api_type,
                currency=body.currency,
                configs=body.configs,
            )
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    overview = await service.list_overview()
    item = next(i for i in overview["bookingApis"] if i["entity"].id == api.id)
    return ApiSuccessResponse(output=BookingApiSerializer.from_overview(item))


@integrations_router.post(
    "/payment-gateways/{gateway_id}/edit",
    response_model=ApiSuccessResponse[PaymentGatewaySerializer],
)
async def update_payment_gateway(
    gateway_id: UUID,
    body: Annotated[UpdatePaymentGatewayBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.edit"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[PaymentGatewaySerializer]:
    try:
        gateway = await service.update_payment_gateway(
            UpdatePaymentGatewayCommand(
                gateway_id=gateway_id,
                status=body.status,
                api_type=body.api_type,
                currency=body.currency,
                convenience_type=body.convenience_type,
                convenience_value=body.convenience_value,
                configs=body.configs,
            )
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    overview = await service.list_overview()
    item = next(i for i in overview["paymentGateways"] if i["entity"].id == gateway.id)
    return ApiSuccessResponse(output=PaymentGatewaySerializer.from_overview(item))


@integrations_router.post(
    "/other-apis/{other_api_id}/edit",
    response_model=ApiSuccessResponse[OtherApiSerializer],
)
async def update_other_api(
    other_api_id: UUID,
    body: Annotated[UpdateOtherApiBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("integrations.edit"))],
    service: Annotated[IntegrationRegistryService, Depends(build_integration_registry_service)],
) -> ApiSuccessResponse[OtherApiSerializer]:
    try:
        other = await service.update_other_api(
            UpdateOtherApiCommand(
                other_api_id=other_api_id,
                status=body.status,
                configs=body.configs,
            )
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    overview = await service.list_overview()
    item = next(i for i in overview["otherApis"] if i["entity"].id == other.id)
    return ApiSuccessResponse(output=OtherApiSerializer.from_overview(item))
