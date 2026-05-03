from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from admin_api.audit_logs.serializers import AuditLogEvent
from admin_api.audit_logs.service import AuditLogService
from common.serializerlib import ApiSuccessResponse, RequestProcessStatus, SearchFilterParams

audit_logs_router = APIRouter()


@audit_logs_router.post(
    "/list",
    response_model=ApiSuccessResponse[list[AuditLogEvent]],
    status_code=200,
    summary="List audit logs for a date range",
    name="List Audit Logs",
)
async def list_audit_logs(
    audit_log_service: Annotated[AuditLogService, Depends(AuditLogService)],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[list[AuditLogEvent]]:
    """
    List audit logs for a given date range.
    """
    # TODO: access control: restrict this endpoint to admin users only
    if (
        search_filter_query.from_date is not None
        and search_filter_query.to_date is not None
        and search_filter_query.from_date > search_filter_query.to_date
    ):
        raise HTTPException(status_code=422, detail="from_date must be before or equal to to_date")

    audit_logs = await audit_log_service.get_list(
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=[AuditLogEvent.from_domain_model(audit_log) for audit_log in audit_logs],
    )
