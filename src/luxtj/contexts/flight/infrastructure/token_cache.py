"""Flight ResultToken cache — Redis-backed (survives uvicorn reload / multi-worker)."""

from __future__ import annotations

from typing import Any

from luxtj.shared_kernel.infrastructure.redis_cache import (
    redis_cache_delete,
    redis_cache_get,
    redis_cache_put,
)

_NAMESPACE = "flight_token"

# Default TTL aligned with Mystifly-style short-lived search/quote tokens (~45 min).
DEFAULT_TOKEN_TTL_SECONDS = 45 * 60


def cache_put(key: str, value: Any, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> None:
    redis_cache_put(_NAMESPACE, key, value, ttl_seconds)


def cache_get(key: str) -> Any | None:
    return redis_cache_get(_NAMESPACE, key)


def cache_delete(key: str) -> None:
    redis_cache_delete(_NAMESPACE, key)
