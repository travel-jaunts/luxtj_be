"""Admin hotel markup CRUD — minimal port for hotel_markup_rules."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import HotelMarkupRuleRow
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel, ApiSuccessResponse
from luxtj.utils import timeutils

hotel_markup_router = APIRouter(prefix="/pricing/hotel-markup", tags=["admin-hotel-markup"])


class MarkupRuleSerializer(ApiSerializerBaseModel):
    id: str
    name: str
    status: str
    supplier_code: str | None = None
    country_code: str | None = None
    city_id: str | None = None
    hotel_code: str | None = None
    star_rating: int | None = None
    check_in_date_from: date | None = None
    check_in_date_to: date | None = None
    markup_amount: float
    is_percentage: bool

    @classmethod
    def from_row(cls, row: HotelMarkupRuleRow) -> "MarkupRuleSerializer":
        return cls(
            id=row.id,
            name=row.name,
            status=row.status,
            supplier_code=row.supplier_code,
            country_code=row.country_code,
            city_id=row.city_id,
            hotel_code=row.hotel_code,
            star_rating=row.star_rating,
            check_in_date_from=row.check_in_date_from,
            check_in_date_to=row.check_in_date_to,
            markup_amount=float(row.markup_amount),
            is_percentage=row.is_percentage,
        )


class MarkupRuleBody(BaseModel):
    name: str
    status: str = "active"
    supplier_code: str | None = None
    country_code: str | None = None
    city_id: str | None = None
    hotel_code: str | None = None
    star_rating: int | None = None
    check_in_date_from: date | None = None
    check_in_date_to: date | None = None
    markup_amount: float = Field(..., ge=0)
    is_percentage: bool = False


@hotel_markup_router.post("/list")
async def list_rules(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.view"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[list[MarkupRuleSerializer]]:
    rows = list(
        (await session.execute(select(HotelMarkupRuleRow).order_by(HotelMarkupRuleRow.created_at.desc())))
        .scalars()
        .all()
    )
    return ApiSuccessResponse(output=[MarkupRuleSerializer.from_row(r) for r in rows])


@hotel_markup_router.post("/create")
async def create_rule(
    body: Annotated[MarkupRuleBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.edit"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[MarkupRuleSerializer]:
    now = timeutils.datetime_now()
    row = HotelMarkupRuleRow(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        status=body.status or "active",
        supplier_code=(body.supplier_code or None),
        country_code=(body.country_code.upper()[:2] if body.country_code else None),
        city_id=body.city_id,
        hotel_code=body.hotel_code,
        star_rating=body.star_rating,
        check_in_date_from=body.check_in_date_from,
        check_in_date_to=body.check_in_date_to,
        markup_amount=Decimal(str(body.markup_amount)),
        is_percentage=body.is_percentage,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return ApiSuccessResponse(output=MarkupRuleSerializer.from_row(row))


@hotel_markup_router.post("/{rule_id}/update")
async def update_rule(
    rule_id: str,
    body: Annotated[MarkupRuleBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.edit"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[MarkupRuleSerializer]:
    row = await session.get(HotelMarkupRuleRow, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Markup rule not found")
    row.name = body.name.strip()
    row.status = body.status or row.status
    row.supplier_code = body.supplier_code
    row.country_code = body.country_code.upper()[:2] if body.country_code else None
    row.city_id = body.city_id
    row.hotel_code = body.hotel_code
    row.star_rating = body.star_rating
    row.check_in_date_from = body.check_in_date_from
    row.check_in_date_to = body.check_in_date_to
    row.markup_amount = Decimal(str(body.markup_amount))
    row.is_percentage = body.is_percentage
    row.updated_at = timeutils.datetime_now()
    await session.flush()
    return ApiSuccessResponse(output=MarkupRuleSerializer.from_row(row))


@hotel_markup_router.post("/{rule_id}/delete")
async def delete_rule(
    rule_id: str,
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.edit"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[dict]:
    row = await session.get(HotelMarkupRuleRow, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Markup rule not found")
    await session.delete(row)
    await session.flush()
    return ApiSuccessResponse(output={"deleted": True, "id": rule_id})
