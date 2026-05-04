from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.reports.marketing.serializers import (
    MarketingNameSearchQuery,
    OfferPerformanceReport,
)
from admin_api.reports.marketing.service import MarketingReportService
from common.serializerlib import ApiSuccessResponse, CurrencyQuery, RequestProcessStatus

marketing_router = APIRouter(prefix="/marketing")


# @marketing_router.post(
#     "/campaigns/performance",
#     response_model=ApiSuccessResponse[CampaignPerformanceReport],
#     status_code=200,
#     summary="Get campaign performance report data",
#     name="Campaign Performance Report Data",
# )
# async def campaign_performance_data(
#     marketing_report_service: Annotated[MarketingReportService, Depends(MarketingReportService)],
#     search_query: Annotated[MarketingNameSearchQuery, Depends()],
#     iso_currency_str: CurrencyQuery = "INR",
# ) -> ApiSuccessResponse[CampaignPerformanceReport]:
#     """
#     Get campaign performance metrics with optional name text filtering.
#     """
#     # TODO: access control: restrict this endpoint to admin users only
#     report = await marketing_report_service.get_campaign_performance(
#         name=search_query.name,
#         iso_currency_str=iso_currency_str,
#     )

#     return ApiSuccessResponse(
#         status=RequestProcessStatus.OK,
#         output=CampaignPerformanceReport.from_domain_model(report),
#     )


@marketing_router.post(
    "/offers/performance",
    response_model=ApiSuccessResponse[OfferPerformanceReport],
    status_code=200,
    summary="Get offer performance report data",
    name="Offer Performance Report Data",
)
async def offer_performance_data(
    marketing_report_service: Annotated[MarketingReportService, Depends(MarketingReportService)],
    search_query: Annotated[MarketingNameSearchQuery, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[OfferPerformanceReport]:
    """
    Get offer performance metrics with optional offer title text filtering.
    """
    # TODO: access control: restrict this endpoint to admin users only
    report = await marketing_report_service.get_offer_performance(
        name=search_query.name,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferPerformanceReport.from_domain_model(report),
    )
