"""Process-lifetime boot cache for activeCurrencies metadata map."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from luxtj.contexts.currency.domain.entities import CurrencyMeta


@dataclass
class ActiveCurrenciesCache:
    """Shape: { CODE → { currency_name, currency_symbol } }."""

    _map: dict[str, dict[str, str]] = field(default_factory=dict)
    _codes: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def replace(self, items: list[CurrencyMeta]) -> None:
        mapping = {
            item.code.upper(): {
                "currency_name": item.currency_name,
                "currency_symbol": item.currency_symbol,
            }
            for item in items
        }
        codes = sorted(mapping.keys())
        with self._lock:
            self._map = mapping
            self._codes = codes

    def get_map(self) -> dict[str, dict[str, str]]:
        with self._lock:
            return {k: dict(v) for k, v in self._map.items()}

    def get_codes(self) -> list[str]:
        with self._lock:
            return list(self._codes)

    def symbol_for(self, code: str, *, default: str = "") -> str:
        with self._lock:
            meta = self._map.get(code.upper())
            if meta is None:
                return default
            return meta.get("currency_symbol") or default


_ACTIVE_CURRENCIES = ActiveCurrenciesCache()


def get_active_currencies_cache() -> ActiveCurrenciesCache:
    return _ACTIVE_CURRENCIES
