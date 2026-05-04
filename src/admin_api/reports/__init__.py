from fastapi import APIRouter

from admin_api.reports.bookings.router import bookings_router
from admin_api.reports.customers.router import customers_router
from admin_api.reports.finance.router import finance_router
from admin_api.reports.partners.router import partners_router
from admin_api.reports.sales.router import sales_router

reports_router = APIRouter(prefix="/reports", tags=["admin_reports"])
reports_router.include_router(sales_router)
reports_router.include_router(partners_router)
reports_router.include_router(finance_router)
reports_router.include_router(bookings_router)
reports_router.include_router(customers_router)
