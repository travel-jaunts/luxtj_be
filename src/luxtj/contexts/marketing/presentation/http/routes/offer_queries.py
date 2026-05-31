from typing import Annotated

from fastapi import APIRouter, Depends

from luxtj.contexts.marketing.application.commands import SearchOffersCommand
from luxtj.contexts.marketing.application.use_cases import OffersService
from luxtj.contexts.marketing.bootstrap import build_offers_service
from luxtj.contexts.marketing.domain.enums import OfferStatusEnum, OfferTypeEnum
from luxtj.contexts.marketing.presentation.http.schemas import OfferSerializer
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse, RequestProcessStatus

router = APIRouter()


@router.post(
    "/search",
    response_model=ApiSuccessResponse[list[OfferSerializer]],
    status_code=200,
    summary="Search offers",
    name="Search Offers",
)
async def search_offers(
    offers_service: Annotated[OffersService, Depends(build_offers_service)],
    name: str | None = None,
    status: OfferStatusEnum | None = None,
    type: OfferTypeEnum | None = None,
) -> ApiSuccessResponse[list[OfferSerializer]]:
    offers = await offers_service.search_offers(
        SearchOffersCommand(name=name, status=status, type=type)
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=[OfferSerializer.from_offer(offer) for offer in offers],
    )
