"""FX conversion service — cache-first rates with pluggable provider."""

from __future__ import annotations

from collections.abc import Callable

from luxtj.bootstrap import config
from luxtj.contexts.currency.application.ports import FxRateProvider
from luxtj.contexts.currency.infrastructure.active_currencies_cache import (
    ActiveCurrenciesCache,
    get_active_currencies_cache,
)
from luxtj.contexts.currency.infrastructure.fx_rate_cache import FxRateCache, get_fx_rate_cache
from luxtj.contexts.currency.infrastructure.stub_rate_provider import StubFxRateProvider
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle

logger = get_logger_handle(__name__)


class CurrencyConversionService:
    """Mirrors TeenvaCurrencyConversion."""

    CURRENCY_CACHE_TTL_MINUTES = 15
    BASE_CURRENCY = "USD"

    def __init__(
        self,
        *,
        rate_provider: FxRateProvider | None = None,
        rate_cache: FxRateCache | None = None,
        active_cache: ActiveCurrenciesCache | None = None,
        active_codes_provider: Callable[[], list[str]] | None = None,
    ) -> None:
        self._provider = rate_provider or StubFxRateProvider()
        self._rate_cache = rate_cache or get_fx_rate_cache()
        self._active_cache = active_cache or get_active_currencies_cache()
        self._active_codes_provider = active_codes_provider

    @staticmethod
    def cache_key(from_currency: str, to_currency: str) -> str:
        return FxRateCache.cache_key(from_currency, to_currency)

    def get_base_currency(self) -> str:
        code = (config.ADMIN_CURRENCY or self.BASE_CURRENCY).upper().strip()
        return code if code else self.BASE_CURRENCY

    def get_active_currency_codes(self) -> list[str]:
        if self._active_codes_provider is not None:
            return [c.upper().strip() for c in self._active_codes_provider() if c and c.strip()]
        return self._active_cache.get_codes()

    def get_pairs(self, base: str | None = None) -> list[tuple[str, str]]:
        base_code = (base or self.get_base_currency()).upper()
        pairs: list[tuple[str, str]] = []
        for to in self.get_active_currency_codes():
            if to == base_code:
                continue
            pairs.append((base_code, to))
        return pairs

    def get_cached_rate(self, from_currency: str, to_currency: str) -> float | None:
        return self._rate_cache.get(from_currency, to_currency)

    def set_cached_rate(self, from_currency: str, to_currency: str, rate: float | None) -> None:
        self._rate_cache.put(from_currency, to_currency, rate)

    def scrape_rates_for_pairs(
        self, pairs: list[tuple[str, str]]
    ) -> list[dict[str, str | float | None]]:
        """Fetch rates via provider (stub or real). Same-currency pairs → 1.0."""
        if not pairs:
            return []
        normalized: list[tuple[str, str]] = []
        results: list[dict[str, str | float | None] | None] = [None] * len(pairs)
        fetch_pairs: list[tuple[str, str]] = []
        fetch_indexes: list[int] = []

        for idx, (frm, to) in enumerate(pairs):
            frm_u = frm.upper()
            to_u = to.upper()
            if frm_u == to_u:
                results[idx] = {"from": frm_u, "to": to_u, "rate": 1.0}
            else:
                fetch_pairs.append((frm_u, to_u))
                fetch_indexes.append(idx)
            normalized.append((frm_u, to_u))

        if fetch_pairs:
            fetched = self._provider.fetch_rates(fetch_pairs)
            for i, item in enumerate(fetched):
                results[fetch_indexes[i]] = item

        return [r if r is not None else {"from": "", "to": "", "rate": None} for r in results]

    def get_rate(self, from_currency: str, to_currency: str) -> float | None:
        frm = from_currency.upper().strip()
        to = to_currency.upper().strip()
        if frm == to:
            return 1.0
        cached = self.get_cached_rate(frm, to)
        if cached is not None:
            return cached
        scraped = self.scrape_rates_for_pairs([(frm, to)])
        rate = scraped[0].get("rate") if scraped else None
        rate_f = float(rate) if isinstance(rate, (int, float)) else None
        self.set_cached_rate(frm, to, rate_f)
        return rate_f

    def refresh_all_rates(self, base: str | None = None) -> list[dict[str, str | float | None]]:
        base_code = (base or self.get_base_currency()).upper()
        pairs = self.get_pairs(base_code)
        if not pairs:
            return []
        scraped = self.scrape_rates_for_pairs(pairs)
        for item in scraped:
            frm = str(item.get("from") or "")
            to = str(item.get("to") or "")
            rate = item.get("rate")
            rate_f = float(rate) if isinstance(rate, (int, float)) else None
            self.set_cached_rate(frm, to, rate_f)
        return scraped


_CONVERSION: CurrencyConversionService | None = None


def get_currency_conversion() -> CurrencyConversionService:
    global _CONVERSION
    if _CONVERSION is None:
        _CONVERSION = CurrencyConversionService()
    return _CONVERSION


def set_currency_conversion(service: CurrencyConversionService) -> None:
    global _CONVERSION
    _CONVERSION = service
