"""Hotel markup service — mirrors TeenvaHotelMarkup."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import NewCitiesNRegionRow
from luxtj.contexts.hotel.application.markup_rule_resolver import HotelMarkupRuleResolver
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import HotelMarkupRuleRow


class HotelMarkup:
    def __init__(
        self,
        session: AsyncSession,
        resolver: HotelMarkupRuleResolver | None = None,
        *,
        crs_session: AsyncSession | None = None,
    ) -> None:
        self._session = session
        self._crs_session = crs_session or session
        self._resolver = resolver or HotelMarkupRuleResolver()
        self._cached_rules: list[HotelMarkupRuleRow] | None = None
        self._region_country_cache: dict[str, str | None] = {}

    async def active_rules(self) -> list[HotelMarkupRuleRow]:
        if self._cached_rules is None:
            stmt = select(HotelMarkupRuleRow).where(
                HotelMarkupRuleRow.status.in_(["active", "ACTIVE", "1"])
            )
            self._cached_rules = list((await self._session.execute(stmt)).scalars().all())
        return self._cached_rules

    async def country_code_for_region_id(self, region_id: str) -> str | None:
        if not region_id:
            return None
        if region_id in self._region_country_cache:
            return self._region_country_cache[region_id]
        region = await self._crs_session.get(NewCitiesNRegionRow, region_id)
        iso = (
            str(region.country_code).upper()[:2]
            if region is not None and region.country_code
            else None
        )
        self._region_country_cache[region_id] = iso
        return iso

    async def build_context(self, params: dict[str, Any]) -> dict[str, Any]:
        region_id = str(params.get("region_id") or "") if params.get("region_id") else ""
        country = params.get("country_code")
        if country is None and region_id:
            country = await self.country_code_for_region_id(region_id)
        check_in = (
            params.get("check_in_date") or params.get("checkin") or params.get("checkin_date")
        )
        star = params.get("star_rating")
        return {
            "supplier_code": HotelMarkupRuleResolver.normalize_supplier_code(
                params.get("supplier_code")
                if isinstance(params.get("supplier_code"), str)
                else None
            ),
            "country_code": HotelMarkupRuleResolver.normalize_country_code(
                country if isinstance(country, str) else None
            ),
            "region_id": region_id or None,
            "hotel_code": HotelMarkupRuleResolver.normalize_filter(
                params.get("hotel_code") if isinstance(params.get("hotel_code"), str) else None
            ),
            "star_rating": int(star) if star not in (None, "") else None,
            "check_in_date": str(check_in).strip()
            if isinstance(check_in, str) and check_in.strip()
            else None,
        }

    async def get_markup_amount_for_hotel(
        self, hotel_params: dict[str, Any], amount: float
    ) -> dict[str, Any]:
        basis = max(0.0, round(float(amount), 2))
        context = await self.build_context(hotel_params)
        rules = await self.active_rules()
        if not rules:
            return {"amount": 0.0, "value": 0.0, "isPercentage": False, "rule_id": None}
        matching = self._resolver.matching_rules(rules, context)
        best = self._resolver.select_best(matching)
        markup_total = self._resolver.compute_markup_value(best, basis)
        return {
            "amount": float(markup_total),
            "value": float(best.markup_amount) if best is not None else 0.0,
            "isPercentage": bool(best.is_percentage) if best is not None else False,
            "rule_id": str(best.id) if best is not None else None,
        }
