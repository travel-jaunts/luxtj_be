"""Admin CRS mapping routes — RateHawk region + hotel stream (Path B)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException

from luxtj.contexts.crs.mapping.application import mapping_control as control
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse

crs_mapping_router = APIRouter(prefix="/crs/mapping", tags=["admin-crs-mapping"])


@crs_mapping_router.post("/ratehawk/region/status")
async def region_status(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.view"))],
) -> ApiSuccessResponse[dict]:
    return ApiSuccessResponse(output=control.region_status())


@crs_mapping_router.post("/ratehawk/region/start")
async def region_start(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.edit"))],
) -> ApiSuccessResponse[dict]:
    try:
        return ApiSuccessResponse(output=control.region_start())
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@crs_mapping_router.post("/ratehawk/region/stop")
async def region_stop(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.edit"))],
) -> ApiSuccessResponse[dict]:
    try:
        return ApiSuccessResponse(output=control.region_stop())
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@crs_mapping_router.post("/ratehawk/region/wipe")
async def region_wipe(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.edit"))],
) -> ApiSuccessResponse[dict]:
    try:
        return ApiSuccessResponse(output=control.region_wipe())
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@crs_mapping_router.post("/ratehawk/hotel/status")
async def hotel_status(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.view"))],
) -> ApiSuccessResponse[dict]:
    return ApiSuccessResponse(output=control.hotel_status())


@crs_mapping_router.post("/ratehawk/hotel/start")
async def hotel_start(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.edit"))],
    body: Annotated[dict[str, Any] | None, Body()] = None,
) -> ApiSuccessResponse[dict]:
    force_new = bool((body or {}).get("force_new") or (body or {}).get("forceNew"))
    try:
        return ApiSuccessResponse(output=control.hotel_start(force_new=force_new))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@crs_mapping_router.post("/ratehawk/hotel/stop")
async def hotel_stop(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.edit"))],
) -> ApiSuccessResponse[dict]:
    try:
        return ApiSuccessResponse(output=control.hotel_stop())
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@crs_mapping_router.post("/ratehawk/hotel/wipe-restart")
async def hotel_wipe_restart(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("crs.mapping.edit"))],
) -> ApiSuccessResponse[dict]:
    try:
        return ApiSuccessResponse(output=control.hotel_wipe_restart())
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
