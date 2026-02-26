from typing import Dict, Any

from fastapi import APIRouter, Request

from app.core.logging import get_logger

router = APIRouter(prefix="/items", tags=["items"])
logger = get_logger(__name__)


@router.get("/")
async def list_items(request: Request) -> Dict[str, Any]:
    user = getattr(request.state, "user", None)
    logger.debug("list_items called by user=%s", user)
    return {"items": [], "request_id": getattr(request.state, "request_id", None)}


@router.get("/{item_id}")
async def get_item(item_id: int, request: Request) -> Dict[str, Any]:
    return {"item_id": item_id, "request_id": getattr(request.state, "request_id", None)}


@router.get("/{item_id}/details")
async def get_item_details(item_id: int, request: Request) -> Dict[str, Any]:
    raise Exception("Simulated exception in get_item_details")
    # return {"item_id": item_id, "details": {}, "request_id": getattr(request.state, "request_id", None)}
