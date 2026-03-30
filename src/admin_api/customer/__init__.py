from fastapi import APIRouter

from admin_api.customer.users.router import user_router

customer_router = APIRouter(prefix="/customers")
customer_router.include_router(user_router)
