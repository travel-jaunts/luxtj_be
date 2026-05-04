from fastapi import APIRouter

from admin_api.reports.sales.router import sales_router

reports_router = APIRouter(prefix="/reports", tags=["admin_reports"])
reports_router.include_router(sales_router)
