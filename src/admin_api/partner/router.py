from fastapi import APIRouter, Depends

from admin_api.partner.activity.router import activity_partner_router
from admin_api.partner.affiliate.router import affiliate_partner_router
from admin_api.partner.agent.router import agent_partner_router
from admin_api.partner.approvals.router import approvals_router
from admin_api.partner.offers.router import offers_partner_router
from admin_api.partner.property.router import property_partner_router
from admin_api.partner.transactions.router import transactions_partner_router
from luxtj.contexts.identity.presentation.http.dependencies import (
    require_any_permission,
    require_permission,
)

partner_router = APIRouter(prefix="/partners", tags=["admin_partner"])
partner_router.include_router(
    activity_partner_router,
    prefix="/activity",
    dependencies=[Depends(require_permission("partners.activity.view"))],
)
partner_router.include_router(
    affiliate_partner_router,
    prefix="/affiliate",
    dependencies=[Depends(require_permission("partners.affiliates.view"))],
)
partner_router.include_router(
    agent_partner_router,
    prefix="/agent",
    dependencies=[Depends(require_permission("partners.b2b.view"))],
)
partner_router.include_router(
    approvals_router,
    prefix="/approvals",
    dependencies=[
        Depends(
            require_any_permission(
                "partners.approvals.view",
                "partners.approvals.kyc.view",
                "partners.approvals.content.view",
            )
        )
    ],
)
partner_router.include_router(
    offers_partner_router,
    prefix="/offers",
    dependencies=[Depends(require_permission("partners.pricing.view"))],
)
partner_router.include_router(
    property_partner_router,
    prefix="/property",
    dependencies=[Depends(require_permission("partners.property.view"))],
)
partner_router.include_router(
    transactions_partner_router,
    prefix="/transactions",
    dependencies=[Depends(require_permission("partners.payments.view"))],
)
