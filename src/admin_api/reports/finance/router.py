from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.reports.finance.serializers import FinanceReport, FinanceReportQuery
from admin_api.reports.finance.service import FinanceReportService
from common.serializerlib import ApiSuccessResponse, CurrencyQuery, RequestProcessStatus

finance_router = APIRouter(prefix="/finance")


@finance_router.post(
    "/data",
    response_model=ApiSuccessResponse[FinanceReport],
    status_code=200,
    summary="Get finance dashboard report data",
    name="Finance Report Data",
)
async def finance_report_data(
    finance_report_service: Annotated[FinanceReportService, Depends(FinanceReportService)],
    report_query: Annotated[FinanceReportQuery, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[FinanceReport]:
    """
    Get finance dashboard data for the overview page.
    """
    # TODO: access control: restrict this endpoint to admin users only
    report = await finance_report_service.get_report(
        from_date=report_query.from_date,
        to_date=report_query.to_date,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=FinanceReport.from_domain_model(report),
    )
