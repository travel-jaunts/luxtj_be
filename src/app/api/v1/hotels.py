from typing import Dict, Any

from fastapi import APIRouter, Request

from app.core.logging import get_logger

router = APIRouter(prefix="/hotels", tags=["hotels"])
logger = get_logger(__name__)


@router.post("/id/{hotel_id}")
async def get_hotel_by_id(hotel_id: int, request: Request) -> Dict[str, Any]:
    return {"hotel_id": hotel_id, "request_id": getattr(request.state, "request_id", None)}
