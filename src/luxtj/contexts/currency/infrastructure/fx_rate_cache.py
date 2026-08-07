"""In-memory TTL cache for FX pair rates."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import monotonic


@dataclass
class _CacheEntry:
    rate: float
    expires_at: float


@dataclass
class FxRateCache:
    ttl_seconds: int = 15 * 60
    _entries: dict[str, _CacheEntry] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    @staticmethod
    def cache_key(from_currency: str, to_currency: str) -> str:
        return f"teenva_currency_rate_{from_currency.upper()}_{to_currency.upper()}"

    def get(self, from_currency: str, to_currency: str) -> float | None:
        key = self.cache_key(from_currency, to_currency)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if monotonic() >= entry.expires_at:
                del self._entries[key]
                return None
            return entry.rate

    def put(self, from_currency: str, to_currency: str, rate: float | None) -> None:
        if rate is None:
            return
        key = self.cache_key(from_currency, to_currency)
        with self._lock:
            self._entries[key] = _CacheEntry(
                rate=float(rate),
                expires_at=monotonic() + self.ttl_seconds,
            )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_FX_CACHE = FxRateCache()


def get_fx_rate_cache() -> FxRateCache:
    return _FX_CACHE
