from typing import Annotated

from fastapi import APIRouter, Depends

from luxtj.contexts.action_centre.application.use_cases import ActionCentreService
from luxtj.contexts.action_centre.bootstrap import build_action_centre_service
from luxtj.contexts.action_centre.presentation.http.schemas import SummarySerializer
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse, RequestProcessStatus

router = APIRouter()


@router.post(
    "/summary",
    response_model=ApiSuccessResponse[SummarySerializer],
    status_code=200,
    summary="Aggregated pending-action cards across registered workflows",
    name="Action Centre Summary",
)
async def get_summary(
    service: Annotated[ActionCentreService, Depends(build_action_centre_service)],
) -> ApiSuccessResponse[SummarySerializer]:
    summary = await service.get_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=SummarySerializer.from_summary(summary),
    )
