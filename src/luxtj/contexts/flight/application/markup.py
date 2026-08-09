"""Flight markup service — mirrors TeenvaFlightMarkup."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.flight.application.markup_rule_resolver import FlightMarkupRuleResolver
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import FlightMarkupRuleRow


class FlightMarkup:
    def __init__(
        self,
        session: AsyncSession,
        resolver: FlightMarkupRuleResolver | None = None,
    ) -> None:
        self._session = session
        self._resolver = resolver or FlightMarkupRuleResolver()
        self._cached_rules: list[FlightMarkupRuleRow] | None = None

    async def active_rules(self) -> list[FlightMarkupRuleRow]:
        if self._cached_rules is None:
            stmt = select(FlightMarkupRuleRow).where(
                FlightMarkupRuleRow.status.in_(["active", "ACTIVE", "1"])
            )
            self._cached_rules = list((await self._session.execute(stmt)).scalars().all())
        return self._cached_rules

    def build_context(self, flight_params: dict[str, Any]) -> dict[str, Any]:
        cabin = flight_params.get("cabin_class") or flight_params.get("cabinClass")
        travel = flight_params.get("travel_departure") or flight_params.get("travelDate")
        return {
            "airline": FlightMarkupRuleResolver.normalize_filter(
                flight_params.get("airline") if isinstance(flight_params.get("airline"), str) else None
            ),
            "origin": FlightMarkupRuleResolver.normalize_filter(
                flight_params.get("origin") if isinstance(flight_params.get("origin"), str) else None
            ),
            "destination": FlightMarkupRuleResolver.normalize_filter(
                flight_params.get("destination")
                if isinstance(flight_params.get("destination"), str)
                else None
            ),
            "cabin_class": FlightMarkupRuleResolver.normalize_cabin_slug(
                cabin if isinstance(cabin, str) else None
            ),
            "travel_departure": str(travel).strip()
            if isinstance(travel, str) and travel.strip()
            else None,
        }

    async def get_markup_amount_for_flight(
        self, flight_params: dict[str, Any], amount: float
    ) -> dict[str, Any]:
        basis = max(0.0, round(float(amount), 2))
        context = self.build_context(flight_params)
        rules = await self.active_rules()
        if not rules:
            return {"amount": 0.0, "value": 0.0, "isPercentage": False, "rule_id": None}
        matching = self._resolver.matching_rules(rules, context)
        best = self._resolver.select_best(matching)
        markup_total = max(0.0, float(self._resolver.compute_markup_value(best, basis)))
        return {
            "amount": float(markup_total),
            "value": float(best.markup_amount) if best is not None else 0.0,
            "isPercentage": bool(best.is_percentage) if best is not None else False,
            "rule_id": str(best.id) if best is not None else None,
        }
