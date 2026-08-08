"""In-process TTL cache for flight ResultToken opaque keys (group / offer / fare / prebook)."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

_lock = Lock()
_store: dict[str, tuple[float, Any]] = {}

# Default TTL aligned with Mystifly-style short-lived search/quote tokens (~45 min).
DEFAULT_TOKEN_TTL_SECONDS = 45 * 60


def cache_put(key: str, value: Any, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> None:
    with _lock:
        _store[key] = (time.time() + ttl_seconds, value)


def cache_get(key: str) -> Any | None:
    with _lock:
        item = _store.get(key)
        if item is None:
            return None
        expires, value = item
        if time.time() > expires:
            _store.pop(key, None)
            return None
        return value


def cache_delete(key: str) -> None:
    with _lock:
        _store.pop(key, None)
