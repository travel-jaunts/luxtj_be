"""In-process cache for BlockRoom snapshots (mirrors Laravel Cache put/get)."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

_lock = Lock()
_store: dict[str, tuple[float, Any]] = {}


def cache_put(key: str, value: Any, ttl_seconds: int) -> None:
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
