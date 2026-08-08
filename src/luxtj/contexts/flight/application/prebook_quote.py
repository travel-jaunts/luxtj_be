"""Flight pre-book quote — mirrors TeenvaFlightPreBookQuote (admin currency)."""

from __future__ import annotations

import base64
import json
from typing import Any


class FlightPreBookQuote:
    @staticmethod
    def round_amount(amount: float) -> float:
        return round(float(amount), 4)

    @staticmethod
    def convenience_amount(pg: Any | None, base_payable: float) -> dict[str, Any]:
        if pg is None:
            return {"amount": 0.0, "type": None, "raw": 0.0}
        raw = float(getattr(pg, "convenience_value", None) or 0)
        if raw <= 0:
            return {"amount": 0.0, "type": None, "raw": 0.0}
        ctype = str(getattr(pg, "convenience_type", None) or "flat").lower()
        if ctype == "percentage":
            return {
                "amount": round((raw * base_payable) / 100, 2),
                "type": "percentage",
                "raw": raw,
            }
        return {"amount": round(raw, 2), "type": "flat", "raw": raw}

    @staticmethod
    def _price_from_key_blob(raw_key: str) -> float | None:
        text = str(raw_key or "").strip()
        if not text:
            return None
        try:
            decoded = base64.b64decode(text, validate=False)
        except Exception:
            return None
        if not decoded:
            return None
        # Prefer JSON blobs written by City Travel ExtraServices.
        try:
            data = json.loads(decoded.decode())
            if isinstance(data, list) and data and isinstance(data[0], dict) and "Price" in data[0]:
                return float(data[0]["Price"])
            if isinstance(data, dict) and "Price" in data:
                return float(data["Price"])
        except Exception:
            pass
        # Mystifly PHP serialize fallback (best-effort Price scrape).
        try:
            import re

            m = re.search(rb'"Price";(?:d|i):([0-9.]+)', decoded)
            if m:
                return float(m.group(1))
            m = re.search(rb"Price[^\d]*([0-9]+(?:\.[0-9]+)?)", decoded)
            if m:
                return float(m.group(1))
        except Exception:
            return None
        return None

    @classmethod
    def _sum_nested_selection(
        cls,
        passengers: list[Any],
        details_key: str,
        blob_key: str,
    ) -> float:
        total = 0.0
        for pax in passengers:
            if not isinstance(pax, dict):
                continue
            details = pax.get(details_key)
            if not isinstance(details, list):
                continue
            for segment_rows in details:
                if not isinstance(segment_rows, list):
                    continue
                for row in segment_rows:
                    if not isinstance(row, dict):
                        continue
                    from_blob = False
                    blob_price = cls._price_from_key_blob(str(row.get(blob_key) or ""))
                    if blob_price is not None:
                        total += blob_price
                        from_blob = True
                    if not from_blob and "Price" in row:
                        total += float(row.get("Price") or 0)
        return cls.round_amount(total)

    @classmethod
    def sum_seat_selection_prices(cls, passengers: list[Any]) -> float:
        return cls._sum_nested_selection(passengers, "SeatDetails", "SeatKey")

    @classmethod
    def sum_baggage_selection_prices(cls, passengers: list[Any]) -> float:
        return cls._sum_nested_selection(passengers, "BaggageDetails", "BaggageKey")

    @classmethod
    def sum_meal_selection_prices(cls, passengers: list[Any]) -> float:
        return cls._sum_nested_selection(passengers, "MealDetails", "MealKey")

    @classmethod
    def compute(
        cls,
        token_data: dict[str, Any],
        discount_data: dict[str, Any] | None,
        passengers: list[Any],
        promo_code: str | None,
        payment_gateway: Any | None,
    ) -> dict[str, Any]:
        """gross − promo − admin discount + SSR → convenience → final (all admin)."""
        price = token_data.get("Price") if isinstance(token_data.get("Price"), dict) else {}
        gross = float(price.get("TotalDisplayFare") or 0)
        discount = discount_data if isinstance(discount_data, dict) else {}
        admin_discount = float(discount.get("amount") or 0)

        # Flight promo engine not wired yet — accept code but apply 0 until Phase promo.
        promo_discount = 0.0
        promo_applied = None
        promo_type = None
        promo_value = 0.0
        _ = (promo_code or "").strip()

        seat_total = cls.sum_seat_selection_prices(passengers)
        baggage_total = cls.sum_baggage_selection_prices(passengers)
        meal_total = cls.sum_meal_selection_prices(passengers)
        # Also sum City Travel "Other" selections if clients send ServiceDetails / SelectedServices prices.
        other_total = cls._sum_nested_selection(passengers, "ServiceDetails", "ServiceKey")

        subtotal = max(
            0.0,
            cls.round_amount(
                gross
                - promo_discount
                - admin_discount
                + seat_total
                + baggage_total
                + meal_total
                + other_total
            ),
        )
        conv = cls.convenience_amount(payment_gateway, subtotal)
        final = max(0.0, cls.round_amount(subtotal + float(conv["amount"] or 0)))

        return {
            "gross_display_fare": cls.round_amount(gross),
            "admin_discount": cls.round_amount(admin_discount),
            "promo_discount": cls.round_amount(promo_discount),
            "promocode_applied": promo_applied,
            "promocode_type": promo_type,
            "promocode_value": round(promo_value, 2),
            "seat_selection_total": seat_total,
            "baggage_selection_total": baggage_total,
            "meal_selection_total": meal_total,
            "other_selection_total": other_total,
            "convenience_fee_amount": float(conv["amount"] or 0),
            "convenience_fee_type": conv.get("type"),
            "convenience_fee_value": float(conv["raw"] or 0),
            "final_total_fare": final,
        }
