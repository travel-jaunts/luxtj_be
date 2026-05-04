from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.reports.operations.serializers import OperationsReport, OperationsReportQuery
from admin_api.reports.operations.service import OperationsReportService
from common.serializerlib import ApiSuccessResponse, RequestProcessStatus

operations_router = APIRouter(prefix="/operations")


@operations_router.post(
    "/data",
    response_model=ApiSuccessResponse[OperationsReport],
    status_code=200,
    summary="Get operations dashboard report data",
    name="Operations Report Data",
)
async def operations_report_data(
    operations_report_service: Annotated[OperationsReportService, Depends(OperationsReportService)],
    report_query: Annotated[OperationsReportQuery, Depends()],
) -> ApiSuccessResponse[OperationsReport]:
    """
    Get operations dashboard data for the overview page.
    """
    # TODO: access control: restrict this endpoint to admin users only
    report = await operations_report_service.get_report(
        from_date=report_query.from_date,
        to_date=report_query.to_date,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OperationsReport.from_domain_model(report),
    )
