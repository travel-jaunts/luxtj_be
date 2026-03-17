from fastapi import APIRouter

from app.api.v1 import items
from app.api.v1 import hotels
from app.api.layers import tourradar
from app.api.admin import admin_base_router

router = APIRouter(prefix="/v1")
router.include_router(items.router)
router.include_router(hotels.router)
router.include_router(tourradar.router)
router.include_router(admin_base_router)
