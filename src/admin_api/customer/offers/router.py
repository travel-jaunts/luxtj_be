from typing import Annotated

from fastapi import APIRouter, Body, Depends

from admin_api.customer.offers.serializers import (
    OfferLineItemSerializer,
    OffersKpiSummarySerializer,
    CreateOfferDetailsBody,
    UpdateOfferDetailsBody,
)
from admin_api.customer.offers.service import CustomerOffersService
from common.serializerlib import (
    ApiSuccessResponse,
    CurrencyQuery,
    PaginatedResult,
    PaginationParams,
    SearchFilterParams,
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
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
    iso_currency: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[OfferLineItemSerializer]]:
    """
    List offers for all customers with pagination
    """
    customer_offers_list, pagination_meta = await offers_service.get_offers_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
        iso_currency_str=iso_currency,
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


@offers_router.post(
    "/create-offer",
    response_model=ApiSuccessResponse[OfferLineItemSerializer],
    status_code=200,
    summary="Create a new offer",
    name="Create Offer",
)
async def create_offer(
    offers_service: Annotated[CustomerOffersService, Depends(CustomerOffersService)],
    create_offer_details: Annotated[CreateOfferDetailsBody, Body(...)],
) -> ApiSuccessResponse[OfferLineItemSerializer]:
    """
    Create a new offer
    """
    # TODO: access control: restrict this endpoint to admin users only
    new_offer = await offers_service.create_offer(create_offer_details.to_dto())
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferLineItemSerializer.from_domain_model(new_offer),
    )


@offers_router.post(
    "/{offer_id}/update",
    response_model=ApiSuccessResponse[OfferLineItemSerializer],
    status_code=200,
    summary="Update an existing offer",
    name="Update Offer",
)
async def update_offer(
    offer_id: str,
    offers_service: Annotated[CustomerOffersService, Depends(CustomerOffersService)],
    update_offer_details: Annotated[UpdateOfferDetailsBody, Body(...)],
) -> ApiSuccessResponse[OfferLineItemSerializer]:
    """
    Update an existing offer
    """
    # TODO: access control: restrict this endpoint to admin users only
    updated_offer = await offers_service.update_offer(
        offer_id=offer_id, update_offer_dto=update_offer_details.to_dto()
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferLineItemSerializer.from_domain_model(updated_offer),
    )


@offers_router.post(
    "/{offer_id}/delete",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Delete an offer",
    name="Delete Offer",
)
async def delete_offer(
    offer_id: str,
    offers_service: Annotated[CustomerOffersService, Depends(CustomerOffersService)],
) -> ApiSuccessResponse[str]:
    """
    Delete an offer
    """
    # TODO: access control: restrict this endpoint to admin users only
    await offers_service.delete_offer(offer_id=offer_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Offer {offer_id} deleted successfully",
    )
