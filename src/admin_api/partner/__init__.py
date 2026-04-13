from fastapi import APIRouter

from admin_api.partner.activity.router import activity_partner_router
from admin_api.partner.affiliate.router import affiliate_partner_router
from admin_api.partner.agent.router import agent_partner_router
from admin_api.partner.property.router import property_partner_router

partner_router = APIRouter(prefix="/partners", tags=["admin_partner"])

partner_router.include_router(activity_partner_router, prefix="/activity")
partner_router.include_router(property_partner_router, prefix="/property")
partner_router.include_router(agent_partner_router, prefix="/agent")
partner_router.include_router(affiliate_partner_router, prefix="/affiliate")
