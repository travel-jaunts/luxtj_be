from fastapi import APIRouter

from luxtj.contexts.action_centre.presentation.http.routes import summary

action_centre_router = APIRouter(prefix="/action-centre", tags=["admin_action_centre"])
action_centre_router.include_router(summary.router)
