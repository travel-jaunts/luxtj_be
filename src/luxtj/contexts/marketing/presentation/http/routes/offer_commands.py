from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends

from luxtj.contexts.marketing.application.commands import (
    DeleteOfferCommand,
    PauseOfferCommand,
    RescindOfferCommand,
    CreateOfferCommand,
)
from luxtj.contexts.marketing.application.use_cases import OffersService
from luxtj.contexts.marketing.bootstrap import build_offers_service
from luxtj.contexts.marketing.domain.errors import OfferDomainError
from luxtj.contexts.marketing.presentation.http.schemas import (
    CreateOfferBody,
    OfferSerializer,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

router = APIRouter()


@router.post(
    "/create",
    response_model=ApiSuccessResponse[OfferSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Create an offer",
    name="Create Offer",
)
async def create_offer(
    offers_service: Annotated[OffersService, Depends(build_offers_service)],
    body: Annotated[CreateOfferBody, Body(...)],
) -> ApiSuccessResponse[OfferSerializer] | ApiErrorResponse:
    command = CreateOfferCommand(
        name=body.name,
        code=body.code,
        type=body.type,
        discount_value=body.discount_value,
        min_booking_value=body.min_booking_value,
        min_booking_value_currency=body.min_booking_value_currency,
        validity_start=body.validity_start,
        validity_end=body.validity_end,
        usage_limit_per_user=body.usage_limit_per_user,
        applicability_on=body.applicability_on,
        stackable=body.stackable,
        auto_apply=body.auto_apply,
    )
    try:
        offer = await offers_service.create_offer(command)
    except OfferDomainError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferSerializer.from_offer(offer),
    )


@router.post(
    "/{offer_id}/pause",
    response_model=ApiSuccessResponse[OfferSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Pause an offer",
    name="Pause Offer",
)
async def pause_offer(
    offer_id: UUID,
    offers_service: Annotated[OffersService, Depends(build_offers_service)],
) -> ApiSuccessResponse[OfferSerializer] | ApiErrorResponse:
    try:
        offer = await offers_service.pause_offer(PauseOfferCommand(offer_id=offer_id))
    except KeyError:
        return ApiErrorResponse(error_message=f"Offer {offer_id} not found")
    except OfferDomainError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferSerializer.from_offer(offer),
    )


@router.post(
    "/{offer_id}/rescind",
    response_model=ApiSuccessResponse[OfferSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Rescind an offer",
    name="Rescind Offer",
)
async def rescind_offer(
    offer_id: UUID,
    offers_service: Annotated[OffersService, Depends(build_offers_service)],
) -> ApiSuccessResponse[OfferSerializer] | ApiErrorResponse:
    try:
        offer = await offers_service.rescind_offer(RescindOfferCommand(offer_id=offer_id))
    except KeyError:
        return ApiErrorResponse(error_message=f"Offer {offer_id} not found")
    except OfferDomainError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferSerializer.from_offer(offer),
    )


@router.post(
    "/{offer_id}/delete",
    response_model=ApiSuccessResponse[OfferSerializer] | ApiErrorResponse,
    status_code=200,
    summary="Delete an offer (soft delete)",
    name="Delete Offer",
)
async def delete_offer(
    offer_id: UUID,
    offers_service: Annotated[OffersService, Depends(build_offers_service)],
) -> ApiSuccessResponse[OfferSerializer] | ApiErrorResponse:
    try:
        offer = await offers_service.delete_offer(DeleteOfferCommand(offer_id=offer_id))
    except KeyError:
        return ApiErrorResponse(error_message=f"Offer {offer_id} not found")

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=OfferSerializer.from_offer(offer),
    )
