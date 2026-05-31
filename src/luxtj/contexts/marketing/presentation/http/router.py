from fastapi import APIRouter

from luxtj.contexts.marketing.presentation.http.routes import (
    campaign_commands,
    campaign_queries,
    offer_commands,
    offer_queries,
)

campaigns_router = APIRouter(prefix="/campaigns")
campaigns_router.include_router(campaign_queries.router)
campaigns_router.include_router(campaign_commands.router)

offers_router = APIRouter(prefix="/offers")
offers_router.include_router(offer_queries.router)
offers_router.include_router(offer_commands.router)

marketing_router = APIRouter(prefix="/marketing", tags=["admin_marketing"])
marketing_router.include_router(campaigns_router)
marketing_router.include_router(offers_router)
