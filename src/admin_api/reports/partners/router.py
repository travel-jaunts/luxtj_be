from typing import Annotated

from fastapi import APIRouter, Depends, Query

from admin_api.reports.partners.serializers import (
    PartnerOption,
    PartnerReport,
    PartnerReportQuery,
    PartnerSearchQuery,
)
from admin_api.reports.partners.service import PartnerReportService
from common.serializerlib import ApiSuccessResponse, CurrencyQuery, RequestProcessStatus

partners_router = APIRouter(prefix="/partners")


@partners_router.post(
    "/data",
    response_model=ApiSuccessResponse[PartnerReport],
    status_code=200,
    summary="Get partner dashboard report data",
    name="Partner Report Data",
)
async def partner_report_data(
    partner_report_service: Annotated[PartnerReportService, Depends(PartnerReportService)],
    report_query: Annotated[PartnerReportQuery, Depends()],
    partner_ids: Annotated[
        list[str] | None,
        Query(
            alias="partnerIds",
            description="Partner IDs used to limit partner performance results",
        ),
    ] = None,
    b2b_partner_ids: Annotated[
        list[str] | None,
        Query(
            alias="b2bPartnerIds",
            description="B2B partner IDs used to limit B2B performance results",
        ),
    ] = None,
    affiliate_ids: Annotated[
        list[str] | None,
        Query(
            alias="affiliateIds",
            description="Affiliate IDs used to limit affiliate performance results",
        ),
    ] = None,
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PartnerReport]:
    """
    Get partner dashboard data using one common response shape for all partner report tabs.
    """
    # TODO: access control: restrict this endpoint to admin users only
    report = await partner_report_service.get_report(
        report_type=report_query.report_type,
        partner_ids=partner_ids,
        b2b_partner_ids=b2b_partner_ids,
        affiliate_ids=affiliate_ids,
        iso_currency_str=iso_currency_str,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PartnerReport.from_domain_model(report),
    )


@partners_router.post(
    "/search",
    response_model=ApiSuccessResponse[list[PartnerOption]],
    status_code=200,
    summary="Search report partners",
    name="Search Report Partners",
)
async def search_report_partners(
    partner_report_service: Annotated[PartnerReportService, Depends(PartnerReportService)],
    partner_query: Annotated[PartnerSearchQuery, Depends()],
) -> ApiSuccessResponse[list[PartnerOption]]:
    """
    Search partner, B2B, or affiliate options for report filters.
    """
    # TODO: access control: restrict this endpoint to admin users only
    partners = await partner_report_service.search_partners(
        partner_type=partner_query.partner_type,
        search_query=partner_query.search_query,
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=[PartnerOption.from_domain_model(partner) for partner in partners],
    )
