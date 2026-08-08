"""Admin API — refund queues."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from admin_api.refund_queues.serializers import (
    FlightRefundIssueBody,
    FlightRefundIssueResultSerializer,
    FlightRefundQueueListBody,
    FlightRefundQueueListResultSerializer,
)
from admin_api.refund_queues.service import FlightRefundQueueService
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_current_principal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiSuccessResponse,
    RequestProcessStatus,
)

refund_queues_router = APIRouter(
    prefix="/refund-queues",
    tags=["admin_refund_queues"],
)


def _flight_service(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    http_client: Annotated[Any, Depends(http_client_handle)],
) -> FlightRefundQueueService:
    return FlightRefundQueueService(session, http_client=http_client)


@refund_queues_router.post(
    "/flight/list",
    response_model=ApiSuccessResponse[FlightRefundQueueListResultSerializer],
    summary="List flight bookings awaiting refund",
    dependencies=[Depends(require_permission("refund_queues.flight.view"))],
)
async def list_flight_refund_queue(
    body: Annotated[FlightRefundQueueListBody, Body(...)],
    service: Annotated[FlightRefundQueueService, Depends(_flight_service)],
) -> ApiSuccessResponse[FlightRefundQueueListResultSerializer]:
    result = await service.list_queue(body)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=result)


@refund_queues_router.post(
    "/flight/issue-refund",
    response_model=ApiSuccessResponse[FlightRefundIssueResultSerializer],
    summary="Issue API or manual refund for a flight payment",
    dependencies=[Depends(require_permission("refund_queues.flight.refund"))],
)
async def issue_flight_refund(
    body: Annotated[FlightRefundIssueBody, Body(...)],
    service: Annotated[FlightRefundQueueService, Depends(_flight_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> ApiSuccessResponse[FlightRefundIssueResultSerializer]:
    try:
        result = await service.issue_refund(
            transaction_id=body.transaction_id,
            refund_amount=body.refund_amount,
            remark=body.remark,
            manual_details=body.manual_details,
                    admin_user_id=str(principal.user_id) if principal.user_id else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=result)
