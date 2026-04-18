from typing import Annotated

from fastapi import APIRouter, Body, Depends

from admin_api.partner.offers.serializers import (
    ActivityPricingLineItem,
    CommissionLineItem,
    CreateOfferBody,
    OfferLineItem,
    OfferPricingSummary,
    PropertyPricingLineItem,
    SeasonalPricingLineItem,
    UpdateActivityPricingBody,
    UpdateCommissionBody,
    UpdateOfferBody,
    UpdatePropertyPricingBody,
    UpdateSeasonalPricingBody,
)
from admin_api.partner.offers.service import PartnerOffersService
from common.serializerlib import (
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)

offers_partner_router = APIRouter()


@offers_partner_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[OfferPricingSummary],
    status_code=200,
    summary="Get pricing and offers summary",
    name="Partner Offers KPI Summary",
)
async def offers_kpi_summary(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
) -> ApiSuccessResponse[OfferPricingSummary]:
    pricing_summary = await offers_service.get_pricing_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferPricingSummary.from_domain_model(pricing_summary),
    )


@offers_partner_router.post(
    "/property-items/list",
    response_model=ApiSuccessResponse[PaginatedResult[PropertyPricingLineItem]],
    status_code=200,
    summary="List property pricing line items",
    name="List Property Pricing Items",
)
async def list_property_items(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[PropertyPricingLineItem]]:
    property_items, pagination_meta = await offers_service.get_property_items(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[PropertyPricingLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[PropertyPricingLineItem.from_domain_model(item) for item in property_items],
        ),
    )


@offers_partner_router.post(
    "/property-items/{property_id}/pricing-update",
    response_model=ApiSuccessResponse[PropertyPricingLineItem],
    status_code=200,
    summary="Update pricing fields for a property line item",
    name="Update Property Pricing Item",
)
async def update_property_item_pricing(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    property_id: str,
    pricing_update: Annotated[UpdatePropertyPricingBody, Body(...)],
) -> ApiSuccessResponse[PropertyPricingLineItem]:
    updated_item = await offers_service.update_property_item_pricing(
        property_id=property_id,
        update_dto=pricing_update.to_dto(),
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PropertyPricingLineItem.from_domain_model(updated_item),
    )


@offers_partner_router.post(
    "/activity-items/list",
    response_model=ApiSuccessResponse[PaginatedResult[ActivityPricingLineItem]],
    status_code=200,
    summary="List activity pricing line items",
    name="List Activity Pricing Items",
)
async def list_activity_items(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[ActivityPricingLineItem]]:
    activity_items, pagination_meta = await offers_service.get_activity_items(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[ActivityPricingLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[ActivityPricingLineItem.from_domain_model(item) for item in activity_items],
        ),
    )


@offers_partner_router.post(
    "/activity-items/{activity_id}/pricing-update",
    response_model=ApiSuccessResponse[ActivityPricingLineItem],
    status_code=200,
    summary="Update pricing fields for an activity line item",
    name="Update Activity Pricing Item",
)
async def update_activity_item_pricing(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    activity_id: str,
    pricing_update: Annotated[UpdateActivityPricingBody, Body(...)],
) -> ApiSuccessResponse[ActivityPricingLineItem]:
    updated_item = await offers_service.update_activity_item_pricing(
        activity_id=activity_id,
        update_dto=pricing_update.to_dto(),
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=ActivityPricingLineItem.from_domain_model(updated_item),
    )


@offers_partner_router.post(
    "/our-commission-items/list",
    response_model=ApiSuccessResponse[PaginatedResult[CommissionLineItem]],
    status_code=200,
    summary="List commission line items",
    name="List Commission Items",
)
async def list_commission_items(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[CommissionLineItem]]:
    commission_items, pagination_meta = await offers_service.get_commission_items(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[CommissionLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[CommissionLineItem.from_domain_model(item) for item in commission_items],
        ),
    )


@offers_partner_router.post(
    "/our-commission-items/{commission_id}/update",
    response_model=ApiSuccessResponse[CommissionLineItem],
    status_code=200,
    summary="Update commission fields for a commission line item",
    name="Update Commission Item",
)
async def update_commission_item(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    commission_id: str,
    commission_update: Annotated[UpdateCommissionBody, Body(...)],
) -> ApiSuccessResponse[CommissionLineItem]:
    updated_item = await offers_service.update_commission_item(
        commission_id=commission_id,
        update_dto=commission_update.to_dto(),
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=CommissionLineItem.from_domain_model(updated_item),
    )


@offers_partner_router.post(
    "/offer-items/list",
    response_model=ApiSuccessResponse[PaginatedResult[OfferLineItem]],
    status_code=200,
    summary="List offer line items",
    name="List Offer Items",
)
async def list_offer_items(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[OfferLineItem]]:
    offer_items, pagination_meta = await offers_service.get_offer_items(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[OfferLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[OfferLineItem.from_domain_model(item) for item in offer_items],
        ),
    )


@offers_partner_router.post(
    "/offer-items/create",
    response_model=ApiSuccessResponse[OfferLineItem],
    status_code=200,
    summary="Create an offer item",
    name="Create Offer Item",
)
async def create_offer_item(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    create_offer_details: Annotated[CreateOfferBody, Body(...)],
) -> ApiSuccessResponse[OfferLineItem]:
    created_offer = await offers_service.create_offer_item(create_offer_details.to_dto())
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferLineItem.from_domain_model(created_offer),
    )


@offers_partner_router.post(
    "/offer-items/{offer_id}/update",
    response_model=ApiSuccessResponse[OfferLineItem],
    status_code=200,
    summary="Update an offer item",
    name="Update Offer Item",
)
async def update_offer_item(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    offer_id: str,
    update_offer_details: Annotated[UpdateOfferBody, Body(...)],
) -> ApiSuccessResponse[OfferLineItem]:
    updated_offer = await offers_service.update_offer_item(
        offer_id=offer_id,
        update_dto=update_offer_details.to_dto(),
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferLineItem.from_domain_model(updated_offer),
    )


@offers_partner_router.post(
    "/seasonal-pricing-items/list",
    response_model=ApiSuccessResponse[PaginatedResult[SeasonalPricingLineItem]],
    status_code=200,
    summary="List seasonal pricing line items",
    name="List Seasonal Pricing Items",
)
async def list_seasonal_pricing_items(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[SeasonalPricingLineItem]]:
    seasonal_items, pagination_meta = await offers_service.get_seasonal_pricing_items(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[SeasonalPricingLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[SeasonalPricingLineItem.from_domain_model(item) for item in seasonal_items],
        ),
    )


@offers_partner_router.post(
    "/seasonal-pricing-items/{seasonal_price_id}/update",
    response_model=ApiSuccessResponse[SeasonalPricingLineItem],
    status_code=200,
    summary="Update a seasonal pricing line item",
    name="Update Seasonal Pricing Item",
)
async def update_seasonal_pricing_item(
    offers_service: Annotated[PartnerOffersService, Depends(PartnerOffersService)],
    seasonal_price_id: str,
    seasonal_pricing_update: Annotated[UpdateSeasonalPricingBody, Body(...)],
) -> ApiSuccessResponse[SeasonalPricingLineItem]:
    updated_item = await offers_service.update_seasonal_pricing_item(
        seasonal_price_id=seasonal_price_id,
        update_dto=seasonal_pricing_update.to_dto(),
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=SeasonalPricingLineItem.from_domain_model(updated_item),
    )
