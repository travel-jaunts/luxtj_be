from fastapi import APIRouter

from admin_api.audit_logs.router import audit_logs_router

admin_audit_logs_router = APIRouter(prefix="/audit-logs", tags=["admin_audit_logs"])
admin_audit_logs_router.include_router(audit_logs_router)
