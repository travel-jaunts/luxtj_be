from fastapi import APIRouter

from admin_api.partner.activity.router import activity_partner_router
from admin_api.partner.affiliate.router import affiliate_partner_router
from admin_api.partner.agent.router import agent_partner_router
from admin_api.partner.approvals.router import approvals_router
from admin_api.partner.offers.router import offers_partner_router
from admin_api.partner.property.router import property_partner_router
from admin_api.partner.transactions.router import transactions_partner_router

partner_router = APIRouter(prefix="/partners", tags=["admin_partner"])

partner_router.include_router(activity_partner_router, prefix="/activity")
partner_router.include_router(approvals_router, prefix="/approvals")
partner_router.include_router(property_partner_router, prefix="/property")
partner_router.include_router(offers_partner_router, prefix="/offers")
partner_router.include_router(agent_partner_router, prefix="/agent")
partner_router.include_router(affiliate_partner_router, prefix="/affiliate")
partner_router.include_router(transactions_partner_router, prefix="/transactions")
