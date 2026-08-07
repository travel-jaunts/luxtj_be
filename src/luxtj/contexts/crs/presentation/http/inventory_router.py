"""Admin CRS hotel inventory routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.crs.application import inventory as inventory_app
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.dependencies import (
    crs_database_session_handle,
    database_session_handle,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse

crs_inventory_router = APIRouter(prefix="/crs/inventory", tags=["admin-crs-inventory"])


class HotelListBody(BaseModel):
    q: str = ""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=50, alias="pageSize")
    status: bool | None = True

    model_config = {"populate_by_name": True}


@crs_inventory_router.post("/hotels/list")
async def list_hotels(
    body: Annotated[HotelListBody, Body()],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("inventory.hotels.view"))
    ],
    crs: Annotated[AsyncSession, Depends(crs_database_session_handle)],
) -> ApiSuccessResponse[dict[str, Any]]:
    result = await inventory_app.list_hotels(
        crs,
        q=body.q,
        page=body.page,
        page_size=body.page_size,
        status=body.status,
    )
    return ApiSuccessResponse(output=result)


@crs_inventory_router.post("/hotels/{hotel_id}")
async def hotel_detail(
    hotel_id: str,
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("inventory.hotels.view"))
    ],
    crs: Annotated[AsyncSession, Depends(crs_database_session_handle)],
    main: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[dict[str, Any]]:
    detail = await inventory_app.get_hotel_detail(crs, main, hotel_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return ApiSuccessResponse(output=detail)


@crs_inventory_router.post("/hotels/{hotel_id}/rooms/{room_id}")
async def room_detail(
    hotel_id: str,
    room_id: str,
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("inventory.hotels.view"))
    ],
    crs: Annotated[AsyncSession, Depends(crs_database_session_handle)],
    main: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[dict[str, Any]]:
    detail = await inventory_app.get_room_detail(crs, main, hotel_id, room_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return ApiSuccessResponse(output=detail)
