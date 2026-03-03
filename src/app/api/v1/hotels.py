from typing import Dict, Any

from fastapi import APIRouter, Request

from app.core.logging import get_logger

router = APIRouter(prefix="/hotels", tags=["hotels"])
logger = get_logger(__name__)


@router.post("/search")
async def get_hotels(request: Request) -> Dict[str, Any]:
    return {
        "status": "ok",
        "data": {
            "hotels": [
                {
                    "id": "hotel_1",
                    "name": "Hotel Sunshine",
                    "location": "Beach City",
                    "rating": 4.5,
                    "price_per_night": 150.0,
                },
                {
                    "id": "hotel_2",
                    "name": "Mountain View Inn",
                    "location": "Hill Town",
                    "rating": 4.0,
                    "price_per_night": 120.0,
                },
            ]
        },
    }
