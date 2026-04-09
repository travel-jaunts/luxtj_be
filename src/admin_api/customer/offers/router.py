from typing import Annotated

from fastapi import APIRouter, Depends

from admin_api.customer.offers.serializers import (
    OfferLineItemSerializer,
    OffersKpiSummarySerializer,
)
from admin_api.customer.offers.service import CustomerOffersService
from common.serializerlib import (
    ApiSuccessResponse,
    CurrencyQuery,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
)

offers_router = APIRouter(prefix="/offers")


@offers_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[OffersKpiSummarySerializer],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
async def offers_kpi_summary(
    offers_service: Annotated[CustomerOffersService, Depends(CustomerOffersService)],
    iso_currency: CurrencyQuery = "INR",
) -> ApiSuccessResponse[OffersKpiSummarySerializer]:
    """
    Get customer offers KPI summary
    """
    offers_kpi_summary = await offers_service.get_kpi_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OffersKpiSummarySerializer.from_domain_model(offers_kpi_summary),
    )


@offers_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[OfferLineItemSerializer]],
    status_code=200,
    summary="List offers for all customers with pagination and filtering",
    name="List Customer Offers",
)
async def list_customer_offers(
    offers_service: Annotated[CustomerOffersService, Depends(CustomerOffersService)],
    query: Annotated[PaginationParams, Depends()],
    iso_currency: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[OfferLineItemSerializer]]:
    """
    List offers for all customers with pagination
    """
    customer_offers_list, pagination_meta = await offers_service.get_offers_list(
        page=query.page, page_size=query.size, iso_currency_str=iso_currency
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[OfferLineItemSerializer](
            items=[
                OfferLineItemSerializer.from_domain_model(offer) for offer in customer_offers_list
            ],
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
        ),
    )
