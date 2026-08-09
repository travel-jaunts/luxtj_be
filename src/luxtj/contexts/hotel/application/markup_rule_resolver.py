"""Hotel markup rule matching — mirrors HotelMarkupRuleResolver."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


class HotelMarkupRuleResolver:
    def matching_rules(
        self, active_rules: list[Any], context: dict[str, Any]
    ) -> list[Any]:
        return [r for r in active_rules if self.rule_matches(r, context)]

    def rule_matches(self, rule: Any, context: dict[str, Any]) -> bool:
        if not self._is_active(rule):
            return False

        sup = self.normalize_supplier_code(getattr(rule, "supplier_code", None))
        ctx_sup = self.normalize_supplier_code(context.get("supplier_code"))
        if sup is not None and (ctx_sup is None or sup != ctx_sup):
            return False

        cc = self.normalize_country_code(getattr(rule, "country_code", None))
        ctx_cc = self.normalize_country_code(context.get("country_code"))
        if cc is not None and (ctx_cc is None or cc != ctx_cc):
            return False

        rule_region = getattr(rule, "region_id", None)
        if rule_region is not None and str(rule_region).strip():
            ctx_region = context.get("region_id")
            if ctx_region is None or str(rule_region) != str(ctx_region):
                return False

        hc = self.normalize_filter(getattr(rule, "hotel_code", None))
        ctx_hc = self.normalize_filter(context.get("hotel_code"))
        if hc is not None and (ctx_hc is None or hc != ctx_hc):
            return False

        rule_star = getattr(rule, "star_rating", None)
        if rule_star is not None:
            if context.get("star_rating") is None or int(rule_star) != int(context["star_rating"]):
                return False

        has_window = (
            getattr(rule, "check_in_date_from", None) is not None
            or getattr(rule, "check_in_date_to", None) is not None
        )
        check_in = self._context_check_in_date(context)
        if has_window:
            if check_in is None:
                return False
            from_d = getattr(rule, "check_in_date_from", None)
            to_d = getattr(rule, "check_in_date_to", None)
            if from_d and check_in < from_d:
                return False
            if to_d and check_in > to_d:
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
        if self.normalize_supplier_code(getattr(rule, "supplier_code", None)) is not None:
            score += 5
        if self.normalize_country_code(getattr(rule, "country_code", None)) is not None:
            score += 4
        region = getattr(rule, "region_id", None)
        if region is not None and str(region).strip():
            score += 4
        if self.normalize_filter(getattr(rule, "hotel_code", None)) is not None:
            score += 6
        if getattr(rule, "star_rating", None) is not None:
            score += 3
        if (
            getattr(rule, "check_in_date_from", None) is not None
            or getattr(rule, "check_in_date_to", None) is not None
        ):
            score += 2
        return score

    def compute_markup_value(self, rule: Any | None, basis_total_fare: float) -> float:
        if rule is None:
            return 0.0
        amount = float(getattr(rule, "markup_amount", 0) or 0)
        if getattr(rule, "is_percentage", False):
            return round(basis_total_fare * (amount / 100.0), 2)
        return round(amount, 2)

    @staticmethod
    def normalize_supplier_code(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.strip().lower()
        return v or None

    @staticmethod
    def normalize_country_code(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.strip().upper()
        return v[:2] if len(v) >= 2 else None

    @staticmethod
    def normalize_filter(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.strip()
        return v or None

    @staticmethod
    def _is_active(rule: Any) -> bool:
        status = getattr(rule, "status", None)
        if isinstance(status, bool):
            return status
        if isinstance(status, str):
            return status.lower() in ("active", "1", "true")
        return False

    @staticmethod
    def _context_check_in_date(context: dict[str, Any]) -> date | None:
        raw = context.get("check_in_date")
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
