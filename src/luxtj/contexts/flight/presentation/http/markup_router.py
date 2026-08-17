"""Admin flight markup CRUD + airport search."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.flight.application.markup_rule_resolver import FlightMarkupRuleResolver
from luxtj.contexts.flight.infrastructure.airport_catalog import search_airports
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import FlightMarkupRuleRow
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel, ApiSuccessResponse
from luxtj.utils import timeutils

flight_markup_router = APIRouter(prefix="/pricing/flight-markup", tags=["admin-flight-markup"])

_CABIN_CHOICES = ("economy", "premium_economy", "business", "first")


class FlightMarkupRuleSerializer(ApiSerializerBaseModel):
    id: str
    name: str
    status: str
    airline: str | None = None
    origin: str | None = None
    destination: str | None = None
    cabin_class: str | None = None
    travel_date_from: date | None = None
    travel_date_to: date | None = None
    markup_amount: float
    is_percentage: bool

    @classmethod
    def from_row(cls, row: FlightMarkupRuleRow) -> FlightMarkupRuleSerializer:
        return cls(
            id=row.id,
            name=row.name,
            status=row.status,
            airline=row.airline,
            origin=row.origin,
            destination=row.destination,
            cabin_class=row.cabin_class,
            travel_date_from=row.travel_date_from,
            travel_date_to=row.travel_date_to,
            markup_amount=float(row.markup_amount),
            is_percentage=row.is_percentage,
        )


class FlightMarkupRuleBody(BaseModel):
    name: str
    status: str = "active"
    airline: str | None = None
    origin: str | None = None
    destination: str | None = None
    cabin_class: str | None = None
    travel_date_from: date | None = None
    travel_date_to: date | None = None
    markup_amount: float = Field(..., ge=0)
    is_percentage: bool = False


class AirportSearchBody(BaseModel):
    query: str = ""
    limit: int = Field(20, ge=1, le=50)


class AirportSerializer(ApiSerializerBaseModel):
    iata: str
    name: str
    city: str
    country: str
    label: str


def _norm_code(value: str | None, *, upper: bool = True) -> str | None:
    v = FlightMarkupRuleResolver.normalize_filter(value)
    if v is None:
        return None
    return v.upper() if upper else v


def _norm_cabin(value: str | None) -> str | None:
    slug = FlightMarkupRuleResolver.normalize_cabin_slug(value)
    if slug is None:
        return None
    if slug not in _CABIN_CHOICES:
        return slug
    return slug


def _apply_body(row: FlightMarkupRuleRow, body: FlightMarkupRuleBody) -> None:
    row.name = body.name.strip()
    row.status = (body.status or "active").strip().lower() or "active"
    row.airline = _norm_code(body.airline)
    row.origin = _norm_code(body.origin)
    row.destination = _norm_code(body.destination)
    row.cabin_class = _norm_cabin(body.cabin_class)
    row.travel_date_from = body.travel_date_from
    row.travel_date_to = body.travel_date_to
    row.markup_amount = Decimal(str(body.markup_amount))
    row.is_percentage = bool(body.is_percentage)
    row.updated_at = timeutils.datetime_now()


@flight_markup_router.post("/list")
async def list_rules(
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("flight_markup.view"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[list[FlightMarkupRuleSerializer]]:
    rows = list(
        (
            await session.execute(
                select(FlightMarkupRuleRow).order_by(FlightMarkupRuleRow.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ApiSuccessResponse(output=[FlightMarkupRuleSerializer.from_row(r) for r in rows])


@flight_markup_router.post("/create")
async def create_rule(
    body: Annotated[FlightMarkupRuleBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("flight_markup.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[FlightMarkupRuleSerializer]:
    now = timeutils.datetime_now()
    row = FlightMarkupRuleRow(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        status=(body.status or "active").strip().lower() or "active",
        airline=_norm_code(body.airline),
        origin=_norm_code(body.origin),
        destination=_norm_code(body.destination),
        cabin_class=_norm_cabin(body.cabin_class),
        travel_date_from=body.travel_date_from,
        travel_date_to=body.travel_date_to,
        markup_amount=Decimal(str(body.markup_amount)),
        is_percentage=bool(body.is_percentage),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return ApiSuccessResponse(output=FlightMarkupRuleSerializer.from_row(row))


@flight_markup_router.post("/{rule_id}/update")
async def update_rule(
    rule_id: str,
    body: Annotated[FlightMarkupRuleBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("flight_markup.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[FlightMarkupRuleSerializer]:
    row = await session.get(FlightMarkupRuleRow, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Markup rule not found")
    _apply_body(row, body)
    await session.flush()
    return ApiSuccessResponse(output=FlightMarkupRuleSerializer.from_row(row))


@flight_markup_router.post("/{rule_id}/delete")
async def delete_rule(
    rule_id: str,
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("flight_markup.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[dict]:
    row = await session.get(FlightMarkupRuleRow, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Markup rule not found")
    await session.delete(row)
    await session.flush()
    return ApiSuccessResponse(output={"deleted": True, "id": rule_id})


@flight_markup_router.post("/airports/search")
async def airports_search(
    body: Annotated[AirportSearchBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("flight_markup.view"))
    ],
) -> ApiSuccessResponse[list[AirportSerializer]]:
    hits = search_airports(body.query, limit=body.limit)
    return ApiSuccessResponse(
        output=[
            AirportSerializer(
                iata=a.iata,
                name=a.name,
                city=a.city,
                country=a.country,
                label=f"{a.iata} — {a.city or a.name} ({a.country})",
            )
            for a in hits
        ]
    )
