from typing import Dict, Any

from fastapi import APIRouter, Request

from app.core.logging import get_logger
from app.api.layers.tourradar.auth import TourradarApiCaller, TourradarApiAccessManager
from app.core.dep_injectors import InProcessAsyncCache

router = APIRouter(prefix="/tours", tags=["tours"])
logger = get_logger(__name__)


@router.post("/currencies")
async def get_hotel_by_id(request: Request) -> Dict[str, Any]:
    service = TourradarApiCaller(
        TourradarApiAccessManager(
            InProcessAsyncCache(),
            request.app.state.http_client,
        ),
        request.app.state.http_client,
    )
    return {"status": "ok", "data": await service.get_currencies()}
