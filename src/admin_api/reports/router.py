from fastapi import APIRouter, Depends

from admin_api.reports.bookings.router import bookings_router
from admin_api.reports.customers.router import customers_router
from admin_api.reports.finance.router import finance_router
from admin_api.reports.marketing.router import marketing_router as marketing_reports_router
from admin_api.reports.operations.router import operations_router
from admin_api.reports.partners.router import partners_router
from admin_api.reports.sales.router import sales_router
from luxtj.contexts.identity.presentation.http.dependencies import require_any_permission

reports_router = APIRouter(prefix="/reports", tags=["admin_reports"])
reports_router.include_router(
    bookings_router,
    dependencies=[
        Depends(require_any_permission("reports.booking.view", "dashboard.view"))
    ],
)
reports_router.include_router(
    customers_router,
    dependencies=[
        Depends(require_any_permission("reports.customer.view", "dashboard.view"))
    ],
)
reports_router.include_router(
    finance_router,
    dependencies=[
        Depends(require_any_permission("reports.finance.view", "dashboard.view"))
    ],
)
reports_router.include_router(
    marketing_reports_router,
    dependencies=[Depends(require_any_permission("reports.marketing.view"))],
)
reports_router.include_router(
    operations_router,
    dependencies=[Depends(require_any_permission("reports.operations.view"))],
)
reports_router.include_router(
    partners_router,
    dependencies=[
        Depends(require_any_permission("reports.partner.view", "dashboard.view"))
    ],
)
reports_router.include_router(
    sales_router,
    dependencies=[
        Depends(require_any_permission("reports.sales.view", "dashboard.view"))
    ],
)
