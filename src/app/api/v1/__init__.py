from fastapi import APIRouter

from app.api.v1 import items

router = APIRouter(prefix="/api/v1")
router.include_router(items.router)
