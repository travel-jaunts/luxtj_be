from fastapi import APIRouter, Depends

from admin_api.customer.bookings.router import bookings_router
from admin_api.customer.offers.router import offers_router
from admin_api.customer.support.router import support_router
from admin_api.customer.transactions.router import transactions_router
from admin_api.customer.users.router import user_router
from luxtj.contexts.identity.presentation.http.dependencies import require_permission

customer_router = APIRouter(prefix="/customers", tags=["admin_customer"])
customer_router.include_router(
    user_router,
    dependencies=[Depends(require_permission("customers.view"))],
)
customer_router.include_router(
    bookings_router,
    dependencies=[Depends(require_permission("customers.bookings.view"))],
)
customer_router.include_router(
    offers_router,
    dependencies=[Depends(require_permission("customers.pricing.view"))],
)
customer_router.include_router(
    support_router,
    dependencies=[Depends(require_permission("customers.support.view"))],
)
customer_router.include_router(
    transactions_router,
    dependencies=[Depends(require_permission("customers.payments.view"))],
)
