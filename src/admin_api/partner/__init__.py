from fastapi import APIRouter

from admin_api.partner.property.router import property_partner_router

partner_router = APIRouter(prefix="/partners", tags=["admin_partner"])

partner_router.include_router(property_partner_router, prefix="/property")
