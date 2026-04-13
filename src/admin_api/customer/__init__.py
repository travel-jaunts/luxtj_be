from fastapi import APIRouter

from admin_api.customer.bookings.router import bookings_router
from admin_api.customer.offers.router import offers_router
from admin_api.customer.support.router import support_router
from admin_api.customer.transactions.router import transactions_router
from admin_api.customer.users.router import user_router

customer_router = APIRouter(prefix="/customers", tags=["admin_customer"])
customer_router.include_router(user_router)
customer_router.include_router(bookings_router)
customer_router.include_router(transactions_router)
customer_router.include_router(support_router)
customer_router.include_router(offers_router)
