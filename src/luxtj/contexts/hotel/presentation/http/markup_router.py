"""Admin hotel markup CRUD + region (city) search."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import NewCitiesNRegionRow
from luxtj.contexts.hotel.application.markup_rule_resolver import HotelMarkupRuleResolver
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import HotelMarkupRuleRow
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.dependencies import (
    crs_database_session_handle,
    database_session_handle,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel, ApiSuccessResponse
from luxtj.utils import timeutils

hotel_markup_router = APIRouter(prefix="/pricing/hotel-markup", tags=["admin-hotel-markup"])


class MarkupRuleSerializer(ApiSerializerBaseModel):
    id: str
    name: str
    status: str
    supplier_code: str | None = None
    country_code: str | None = None
    region_id: str | None = None
    region_name: str | None = None
    hotel_code: str | None = None
    star_rating: int | None = None
    check_in_date_from: date | None = None
    check_in_date_to: date | None = None
    markup_amount: float
    is_percentage: bool

    @classmethod
    def from_row(
        cls, row: HotelMarkupRuleRow, *, region_name: str | None = None
    ) -> "MarkupRuleSerializer":
        return cls(
            id=row.id,
            name=row.name,
            status=row.status,
            supplier_code=row.supplier_code,
            country_code=row.country_code,
            region_id=row.region_id,
            region_name=region_name,
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
    region_id: str | None = None
    hotel_code: str | None = None
    star_rating: int | None = Field(None, ge=1, le=5)
    check_in_date_from: date | None = None
    check_in_date_to: date | None = None
    markup_amount: float = Field(..., ge=0)
    is_percentage: bool = False


class RegionSearchBody(BaseModel):
    query: str = ""
    limit: int = Field(20, ge=1, le=50)


class RegionSerializer(ApiSerializerBaseModel):
    id: str
    name: str
    type: str
    country_code: str
    country_name: str
    label: str


async def _region_names(
    crs_session: AsyncSession, region_ids: list[str]
) -> dict[str, str]:
    ids = [r for r in region_ids if r]
    if not ids:
        return {}
    rows = list(
        (await crs_session.execute(select(NewCitiesNRegionRow).where(NewCitiesNRegionRow.id.in_(ids))))
        .scalars()
        .all()
    )
    return {r.id: r.name for r in rows}


def _apply_body(row: HotelMarkupRuleRow, body: MarkupRuleBody) -> None:
    row.name = body.name.strip()
    row.status = (body.status or "active").strip().lower() or "active"
    row.supplier_code = HotelMarkupRuleResolver.normalize_supplier_code(body.supplier_code)
    row.country_code = HotelMarkupRuleResolver.normalize_country_code(body.country_code)
    rid = (body.region_id or "").strip() or None
    row.region_id = rid
    row.hotel_code = HotelMarkupRuleResolver.normalize_filter(body.hotel_code)
    row.star_rating = body.star_rating
    row.check_in_date_from = body.check_in_date_from
    row.check_in_date_to = body.check_in_date_to
    row.markup_amount = Decimal(str(body.markup_amount))
    row.is_percentage = bool(body.is_percentage)
    row.updated_at = timeutils.datetime_now()


@hotel_markup_router.post("/list")
async def list_rules(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.view"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    crs_session: Annotated[AsyncSession, Depends(crs_database_session_handle)],
) -> ApiSuccessResponse[list[MarkupRuleSerializer]]:
    rows = list(
        (await session.execute(select(HotelMarkupRuleRow).order_by(HotelMarkupRuleRow.created_at.desc())))
        .scalars()
        .all()
    )
    names = await _region_names(crs_session, [r.region_id or "" for r in rows])
    return ApiSuccessResponse(
        output=[
            MarkupRuleSerializer.from_row(r, region_name=names.get(r.region_id or ""))
            for r in rows
        ]
    )


@hotel_markup_router.post("/create")
async def create_rule(
    body: Annotated[MarkupRuleBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.edit"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    crs_session: Annotated[AsyncSession, Depends(crs_database_session_handle)],
) -> ApiSuccessResponse[MarkupRuleSerializer]:
    now = timeutils.datetime_now()
    row = HotelMarkupRuleRow(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        status=(body.status or "active").strip().lower() or "active",
        supplier_code=HotelMarkupRuleResolver.normalize_supplier_code(body.supplier_code),
        country_code=HotelMarkupRuleResolver.normalize_country_code(body.country_code),
        region_id=(body.region_id or "").strip() or None,
        hotel_code=HotelMarkupRuleResolver.normalize_filter(body.hotel_code),
        star_rating=body.star_rating,
        check_in_date_from=body.check_in_date_from,
        check_in_date_to=body.check_in_date_to,
        markup_amount=Decimal(str(body.markup_amount)),
        is_percentage=bool(body.is_percentage),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    names = await _region_names(crs_session, [row.region_id or ""])
    return ApiSuccessResponse(
        output=MarkupRuleSerializer.from_row(
            row, region_name=names.get(row.region_id or "")
        )
    )


@hotel_markup_router.post("/{rule_id}/update")
async def update_rule(
    rule_id: str,
    body: Annotated[MarkupRuleBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.edit"))],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    crs_session: Annotated[AsyncSession, Depends(crs_database_session_handle)],
) -> ApiSuccessResponse[MarkupRuleSerializer]:
    row = await session.get(HotelMarkupRuleRow, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Markup rule not found")
    _apply_body(row, body)
    await session.flush()
    names = await _region_names(crs_session, [row.region_id or ""])
    return ApiSuccessResponse(
        output=MarkupRuleSerializer.from_row(
            row, region_name=names.get(row.region_id or "")
        )
    )


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


@hotel_markup_router.post("/regions/search")
async def regions_search(
    body: Annotated[RegionSearchBody, Body(...)],
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_permission("hotel_markup.view"))],
    crs_session: Annotated[AsyncSession, Depends(crs_database_session_handle)],
) -> ApiSuccessResponse[list[RegionSerializer]]:
    q = (body.query or "").strip()
    if len(q) < 1:
        return ApiSuccessResponse(output=[])
    pattern = f"%{q}%"
    stmt = (
        select(NewCitiesNRegionRow)
        .where(
            or_(
                NewCitiesNRegionRow.name.ilike(pattern),
                NewCitiesNRegionRow.country_name.ilike(pattern),
                NewCitiesNRegionRow.country_code.ilike(pattern),
            )
        )
        .order_by(NewCitiesNRegionRow.name.asc())
        .limit(body.limit)
    )
    rows = list((await crs_session.execute(stmt)).scalars().all())
    return ApiSuccessResponse(
        output=[
            RegionSerializer(
                id=r.id,
                name=r.name,
                type=r.type,
                country_code=r.country_code,
                country_name=r.country_name,
                label=f"{r.name} — {r.country_name or r.country_code}",
            )
            for r in rows
        ]
    )
