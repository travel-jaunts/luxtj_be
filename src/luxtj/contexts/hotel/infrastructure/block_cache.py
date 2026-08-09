"""Hotel BlockRoom snapshot cache — Redis-backed."""

from __future__ import annotations

from typing import Any

from luxtj.shared_kernel.infrastructure.redis_cache import (
    redis_cache_delete,
    redis_cache_get,
    redis_cache_put,
)

_NAMESPACE = "hotel_block"


def cache_put(key: str, value: Any, ttl_seconds: int) -> None:
    redis_cache_put(_NAMESPACE, key, value, ttl_seconds)


def cache_get(key: str) -> Any | None:
    return redis_cache_get(_NAMESPACE, key)


def cache_delete(key: str) -> None:
    redis_cache_delete(_NAMESPACE, key)
