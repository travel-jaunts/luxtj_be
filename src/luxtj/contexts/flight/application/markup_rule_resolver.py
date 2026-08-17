"""Flight markup rule matching — mirrors FlightMarkupRuleResolver."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


class FlightMarkupRuleResolver:
    AMOUNT_DECIMALS = 4

    def matching_rules(self, active_rules: list[Any], context: dict[str, Any]) -> list[Any]:
        return [r for r in active_rules if self.rule_matches(r, context)]

    def rule_matches(self, rule: Any, context: dict[str, Any]) -> bool:
        if not self._is_active(rule):
            return False

        airline = self.normalize_filter(getattr(rule, "airline", None))
        ctx_airline = self.normalize_filter(context.get("airline"))
        if airline is not None and airline.upper() != (ctx_airline or "").upper():
            return False

        origin = self.normalize_filter(getattr(rule, "origin", None))
        ctx_origin = self.normalize_filter(context.get("origin"))
        if origin is not None and origin.upper() != (ctx_origin or "").upper():
            return False

        dest = self.normalize_filter(getattr(rule, "destination", None))
        ctx_dest = self.normalize_filter(context.get("destination"))
        if dest is not None and dest.upper() != (ctx_dest or "").upper():
            return False

        cabin = self.normalize_cabin_slug(self.normalize_filter(getattr(rule, "cabin_class", None)))
        ctx_cabin = self.normalize_cabin_slug(self.normalize_filter(context.get("cabin_class")))
        if cabin is not None and cabin != ctx_cabin:
            return False

        has_window = (
            getattr(rule, "travel_date_from", None) is not None
            or getattr(rule, "travel_date_to", None) is not None
        )
        departure = self._context_departure_date(context)
        if has_window:
            if departure is None:
                return False
            from_d = getattr(rule, "travel_date_from", None)
            to_d = getattr(rule, "travel_date_to", None)
            if from_d and departure < from_d:
                return False
            if to_d and departure > to_d:
                return False
        return True

    def select_best(self, candidates: list[Any]) -> Any | None:
        if not candidates:
            return None
        max_score = max(self.priority_score(r) for r in candidates)
        top = [r for r in candidates if self.priority_score(r) == max_score]
        return sorted(top, key=lambda r: str(getattr(r, "id", "")))[0]

    def priority_score(self, rule: Any) -> int:
        score = 0
        if self.normalize_filter(getattr(rule, "airline", None)) is not None:
            score += 5
        if self.normalize_filter(getattr(rule, "origin", None)) is not None:
            score += 4
        if self.normalize_filter(getattr(rule, "destination", None)) is not None:
            score += 4
        if (
            self.normalize_cabin_slug(self.normalize_filter(getattr(rule, "cabin_class", None)))
            is not None
        ):
            score += 3
        if (
            getattr(rule, "travel_date_from", None) is not None
            or getattr(rule, "travel_date_to", None) is not None
        ):
            score += 2
        return score

    def compute_markup_value(self, rule: Any | None, basis_total_fare: float) -> float:
        if rule is None:
            return 0.0
        amount = float(getattr(rule, "markup_amount", 0) or 0)
        if getattr(rule, "is_percentage", False):
            return round(basis_total_fare * (amount / 100.0), self.AMOUNT_DECIMALS)
        return round(amount, self.AMOUNT_DECIMALS)

    @staticmethod
    def normalize_filter(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.strip()
        return v or None

    @classmethod
    def normalize_cabin_slug(cls, cabin_class: str | None) -> str | None:
        raw = (cls.normalize_filter(cabin_class) or "").lower()
        if not raw:
            return None
        if "first" in raw:
            return "first"
        if "business" in raw:
            return "business"
        if "premium" in raw:
            return "premium_economy"
        if "economy" in raw or "coach" in raw or raw in {"y", "m"}:
            return "economy"
        return raw

    @staticmethod
    def _is_active(rule: Any) -> bool:
        status = getattr(rule, "status", None)
        if isinstance(status, bool):
            return status
        if isinstance(status, str):
            return status.lower() in ("active", "1", "true")
        return False

    @staticmethod
    def _context_departure_date(context: dict[str, Any]) -> date | None:
        raw = context.get("travel_departure")
        if isinstance(raw, date) and not isinstance(raw, datetime):
            return raw
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, str) and raw:
            try:
                return date.fromisoformat(raw[:10])
            except Exception:
                return None
        return None
