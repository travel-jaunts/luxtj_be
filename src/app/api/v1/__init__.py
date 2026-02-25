from fastapi import APIRouter

from app.api.v1 import items

router = APIRouter(prefix="/v1")
router.include_router(items.router)
