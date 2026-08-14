"""Admin promo codes — flight & hotel CRUD over marketing_offers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.contexts.marketing.domain.enums import OfferStatusEnum, OfferTypeEnum
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import MarketingOfferRow
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel, ApiSuccessResponse
from luxtj.utils import timeutils

promo_codes_router = APIRouter(prefix="/promo-codes", tags=["admin_promo_codes"])

ModuleCode = Literal["FLIGHT", "HOTEL"]

_DISCOUNT_TYPES = frozenset({"percentage", "plus", "flat", "percentage_off"})


class PromoCodeSerializer(ApiSerializerBaseModel):
    id: str
    name: str
    code: str
    module: str
    discount_type: str
    discount_value: float
    min_booking_value: float
    currency: str
    validity_start: datetime
    validity_end: datetime
    usage_limit_per_user: int | None = None
    status: str

    @classmethod
    def from_row(cls, row: MarketingOfferRow, *, module: str) -> PromoCodeSerializer:
        otype = str(row.type or "").lower()
        discount_type = (
            "percentage"
            if otype in (OfferTypeEnum.PERCENTAGE_OFF.value, "percentage", "percentage_off")
            else "plus"
        )
        return cls(
            id=row.id,
            name=row.name,
            code=row.code,
            module=module,
            discount_type=discount_type,
            discount_value=float(row.discount_value or 0),
            min_booking_value=float(row.min_booking_value or 0),
            currency=str(row.min_booking_value_currency or AdminCurrency.code()),
            validity_start=row.validity_start,
            validity_end=row.validity_end,
            usage_limit_per_user=row.usage_limit_per_user,
            status=str(row.status or ""),
        )


class PromoCodeBody(BaseModel):
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=2, max_length=32)
    discount_type: str = Field("percentage", description="percentage | plus")
    discount_value: float = Field(..., gt=0)
    min_booking_value: float = Field(0, ge=0)
    currency: str | None = None
    validity_start: datetime
    validity_end: datetime
    usage_limit_per_user: int | None = Field(None, ge=1)
    status: str = "active"


class PromoCodeListBody(BaseModel):
    search: str | None = None
    status: str | None = None


def _applies_to(row: MarketingOfferRow, module: ModuleCode) -> bool:
    apps = row.applicability_on if isinstance(row.applicability_on, list) else []
    if not apps:
        return False
    return any(str(a).upper() in (module, "ALL", "*") for a in apps)


async def _find_code_clash(
    session: AsyncSession,
    *,
    code: str,
    module: ModuleCode,
    exclude_id: str | None = None,
) -> MarketingOfferRow | None:
    """Same code is allowed across modules; clash only within the same module."""
    rows = list(
        (
            await session.execute(
                select(MarketingOfferRow).where(func.upper(MarketingOfferRow.code) == code)
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        if exclude_id and row.id == exclude_id:
            continue
        if str(row.status) == OfferStatusEnum.DELETED.value:
            continue
        if _applies_to(row, module):
            return row
    return None


def _normalize_discount_type(raw: str) -> str:
    t = (raw or "").strip().lower()
    if t not in _DISCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="discount_type must be percentage or plus")
    if t in ("percentage", "percentage_off"):
        return OfferTypeEnum.PERCENTAGE_OFF.value
    return OfferTypeEnum.FLAT.value


def _normalize_code(code: str) -> str:
    c = (code or "").strip().upper()
    if not c:
        raise HTTPException(status_code=400, detail="Promo code is required")
    return c


def _ensure_dates(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    if end <= start:
        raise HTTPException(status_code=400, detail="validity_end must be after validity_start")
    return start, end


def _status_or_default(status: str | None) -> str:
    s = (status or "active").strip().lower()
    if s not in {
        OfferStatusEnum.ACTIVE.value,
        OfferStatusEnum.PAUSED.value,
        OfferStatusEnum.EXPIRED.value,
        OfferStatusEnum.RESCINDED.value,
    }:
        raise HTTPException(status_code=400, detail="Invalid status")
    return s


async def _list_module(
    session: AsyncSession,
    module: ModuleCode,
    body: PromoCodeListBody,
) -> list[PromoCodeSerializer]:
    rows = list(
        (
            await session.execute(
                select(MarketingOfferRow)
                .where(MarketingOfferRow.status != OfferStatusEnum.DELETED.value)
                .order_by(MarketingOfferRow.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    search = (body.search or "").strip().lower()
    status_f = (body.status or "").strip().lower() or None
    out: list[PromoCodeSerializer] = []
    for row in rows:
        if not _applies_to(row, module):
            continue
        if status_f and str(row.status).lower() != status_f:
            continue
        if search:
            blob = f"{row.name} {row.code}".lower()
            if search not in blob:
                continue
        out.append(PromoCodeSerializer.from_row(row, module=module))
    return out


async def _create_module(
    session: AsyncSession,
    module: ModuleCode,
    body: PromoCodeBody,
) -> PromoCodeSerializer:
    code = _normalize_code(body.code)
    offer_type = _normalize_discount_type(body.discount_type)
    if offer_type == OfferTypeEnum.PERCENTAGE_OFF.value and body.discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100")
    start, end = _ensure_dates(body.validity_start, body.validity_end)
    status = _status_or_default(body.status)

    existing = await _find_code_clash(session, code=code, module=module)
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Promo code '{code}' already exists for {module.lower()}",
        )

    now = timeutils.datetime_now()
    currency = (body.currency or AdminCurrency.code() or "INR").upper()[:8]
    row = MarketingOfferRow(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        code=code,
        type=offer_type,
        discount_value=float(body.discount_value),
        min_booking_value=float(body.min_booking_value or 0),
        min_booking_value_currency=currency,
        validity_start=start,
        validity_end=end,
        usage_limit_per_user=body.usage_limit_per_user,
        applicability_on=[module],
        stackable=False,
        auto_apply=False,
        status=status,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    session.add(row)
    await session.flush()
    return PromoCodeSerializer.from_row(row, module=module)


async def _update_module(
    session: AsyncSession,
    module: ModuleCode,
    promo_id: str,
    body: PromoCodeBody,
) -> PromoCodeSerializer:
    row = await session.get(MarketingOfferRow, promo_id)
    if (
        row is None
        or str(row.status) == OfferStatusEnum.DELETED.value
        or not _applies_to(row, module)
    ):
        raise HTTPException(status_code=404, detail="Promo code not found")

    code = _normalize_code(body.code)
    offer_type = _normalize_discount_type(body.discount_type)
    if offer_type == OfferTypeEnum.PERCENTAGE_OFF.value and body.discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100")
    start, end = _ensure_dates(body.validity_start, body.validity_end)

    clash = await _find_code_clash(session, code=code, module=module, exclude_id=promo_id)
    if clash is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Promo code '{code}' already exists for {module.lower()}",
        )

    row.name = body.name.strip()
    row.code = code
    row.type = offer_type
    row.discount_value = float(body.discount_value)
    row.min_booking_value = float(body.min_booking_value or 0)
    row.min_booking_value_currency = (body.currency or AdminCurrency.code() or "INR").upper()[:8]
    row.validity_start = start
    row.validity_end = end
    row.usage_limit_per_user = body.usage_limit_per_user
    row.applicability_on = [module]
    row.status = _status_or_default(body.status)
    row.updated_at = timeutils.datetime_now()
    await session.flush()
    return PromoCodeSerializer.from_row(row, module=module)


async def _delete_module(
    session: AsyncSession,
    module: ModuleCode,
    promo_id: str,
) -> dict:
    row = await session.get(MarketingOfferRow, promo_id)
    if (
        row is None
        or str(row.status) == OfferStatusEnum.DELETED.value
        or not _applies_to(row, module)
    ):
        raise HTTPException(status_code=404, detail="Promo code not found")
    now = timeutils.datetime_now()
    row.status = OfferStatusEnum.DELETED.value
    row.deleted_at = now
    row.updated_at = now
    await session.flush()
    return {"deleted": True, "id": promo_id}


@promo_codes_router.post("/flight/list")
async def list_flight_promo_codes(
    body: Annotated[PromoCodeListBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.flight.view"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[list[PromoCodeSerializer]]:
    return ApiSuccessResponse(output=await _list_module(session, "FLIGHT", body))


@promo_codes_router.post("/flight/create")
async def create_flight_promo_code(
    body: Annotated[PromoCodeBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.flight.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[PromoCodeSerializer]:
    return ApiSuccessResponse(output=await _create_module(session, "FLIGHT", body))


@promo_codes_router.post("/flight/{promo_id}/update")
async def update_flight_promo_code(
    promo_id: str,
    body: Annotated[PromoCodeBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.flight.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[PromoCodeSerializer]:
    return ApiSuccessResponse(output=await _update_module(session, "FLIGHT", promo_id, body))


@promo_codes_router.post("/flight/{promo_id}/delete")
async def delete_flight_promo_code(
    promo_id: str,
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.flight.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[dict]:
    return ApiSuccessResponse(output=await _delete_module(session, "FLIGHT", promo_id))


@promo_codes_router.post("/hotel/list")
async def list_hotel_promo_codes(
    body: Annotated[PromoCodeListBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.hotel.view"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[list[PromoCodeSerializer]]:
    return ApiSuccessResponse(output=await _list_module(session, "HOTEL", body))


@promo_codes_router.post("/hotel/create")
async def create_hotel_promo_code(
    body: Annotated[PromoCodeBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.hotel.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[PromoCodeSerializer]:
    return ApiSuccessResponse(output=await _create_module(session, "HOTEL", body))


@promo_codes_router.post("/hotel/{promo_id}/update")
async def update_hotel_promo_code(
    promo_id: str,
    body: Annotated[PromoCodeBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.hotel.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[PromoCodeSerializer]:
    return ApiSuccessResponse(output=await _update_module(session, "HOTEL", promo_id, body))


@promo_codes_router.post("/hotel/{promo_id}/delete")
async def delete_hotel_promo_code(
    promo_id: str,
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("promo_codes.hotel.edit"))
    ],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ApiSuccessResponse[dict]:
    return ApiSuccessResponse(output=await _delete_module(session, "HOTEL", promo_id))
