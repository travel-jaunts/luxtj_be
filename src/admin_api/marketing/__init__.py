from fastapi import APIRouter

from admin_api.marketing.campaigns.router import campaigns_router

marketing_router = APIRouter(prefix="/marketing", tags=["admin_marketing"])
marketing_router.include_router(campaigns_router)
