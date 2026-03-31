from fastapi import APIRouter

from admin_api.customer.users.router import user_router
from admin_api.customer.bookings.router import bookings_router
from admin_api.customer.payments.router import payments_router

customer_router = APIRouter(prefix="/customers")
customer_router.include_router(user_router)
customer_router.include_router(bookings_router)
customer_router.include_router(payments_router)
