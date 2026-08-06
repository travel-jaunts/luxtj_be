from fastapi import APIRouter, Depends

from luxtj.contexts.action_centre.presentation.http.routes import summary
from luxtj.contexts.identity.presentation.http.dependencies import require_permission

action_centre_router = APIRouter(
    prefix="/action-centre",
    tags=["admin_action_centre"],
    dependencies=[Depends(require_permission("action_centre.view"))],
)
action_centre_router.include_router(summary.router)
