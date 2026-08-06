from fastapi import APIRouter, Depends

from luxtj.contexts.identity.presentation.http.dependencies import (
    require_any_permission,
)
from luxtj.contexts.marketing.presentation.http.routes import (
    campaign_commands,
    campaign_queries,
    offer_commands,
    offer_queries,
)

campaigns_router = APIRouter(
    prefix="/campaigns",
    dependencies=[
        Depends(
            require_any_permission(
                "marketing.view",
                "marketing.campaigns.view",
            )
        )
    ],
)
campaigns_router.include_router(campaign_queries.router)
campaigns_router.include_router(campaign_commands.router)

offers_router = APIRouter(
    prefix="/offers",
    dependencies=[
        Depends(
            require_any_permission(
                "marketing.view",
                "marketing.promos.view",
            )
        )
    ],
)
offers_router.include_router(offer_queries.router)
offers_router.include_router(offer_commands.router)

marketing_router = APIRouter(prefix="/marketing", tags=["admin_marketing"])
marketing_router.include_router(campaigns_router)
marketing_router.include_router(offers_router)
