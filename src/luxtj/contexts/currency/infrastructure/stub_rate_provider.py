"""Stub FX provider with fixed rates for development (no external scrape)."""

from __future__ import annotations

# Approximate mid-market style stubs vs USD for local/dev.
_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.0,
    "JPY": 150.0,
    "AED": 3.67,
    "AUD": 1.52,
    "CAD": 1.36,
    "CHF": 0.88,
    "SGD": 1.35,
    "THB": 35.0,
    "MYR": 4.70,
    "CNY": 7.20,
    "HKD": 7.80,
    "NZD": 1.65,
    "SAR": 3.75,
    "KRW": 1350.0,
}


class StubFxRateProvider:
    def fetch_rates(self, pairs: list[tuple[str, str]]) -> list[dict[str, str | float | None]]:
        results: list[dict[str, str | float | None]] = []
        for from_cur, to_cur in pairs:
            frm = from_cur.upper()
            to = to_cur.upper()
            if frm == to:
                results.append({"from": frm, "to": to, "rate": 1.0})
                continue
            rate = self._rate(frm, to)
            results.append({"from": frm, "to": to, "rate": rate})
        return results

    def _rate(self, frm: str, to: str) -> float | None:
        from_usd = _USD_RATES.get(frm)
        to_usd = _USD_RATES.get(to)
        if from_usd is None or to_usd is None or from_usd <= 0:
            return None
        # 1 FROM = (to_per_usd / from_per_usd) TO
        return round(to_usd / from_usd, 6)
