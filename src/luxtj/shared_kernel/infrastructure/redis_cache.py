"""Shared Redis-backed TTL cache for LuxTJ (flight tokens, hotel blocks, HTTP)."""

from __future__ import annotations

import logging
import os
import pickle
import threading
from typing import Any

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: Any | None = None
_client_failed = False


def redis_url() -> str:
    return (os.environ.get("LTJBE_REDIS_URL") or "redis://127.0.0.1:6379/0").strip()


def get_redis_client() -> Any | None:
    """Lazy Redis client. Returns None if Redis is unreachable (after first failure until reset)."""
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed:
        return None
    with _client_lock:
        if _client is not None:
            return _client
        if _client_failed:
            return None
        try:
            import redis

            client = redis.Redis.from_url(
                redis_url(),
                decode_responses=False,
                socket_connect_timeout=1.5,
                socket_timeout=2.0,
            )
            client.ping()
            _client = client
            logger.info("Redis cache connected (%s)", redis_url())
            return _client
        except Exception:
            _client_failed = True
            logger.exception(
                "Redis unavailable at %s — TTL caches will miss until process restart",
                redis_url(),
            )
            return None


def reset_redis_client() -> None:
    """Test helper: drop cached client / failure latch."""
    global _client, _client_failed
    with _client_lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = None
        _client_failed = False


def namespaced_key(namespace: str, key: str) -> str:
    ns = (namespace or "luxtj").strip(":")
    return f"luxtj:{ns}:{key}"


def redis_cache_put(namespace: str, key: str, value: Any, ttl_seconds: int) -> bool:
    """Serialize ``value`` with pickle and SETEX. Returns True on success."""
    client = get_redis_client()
    if client is None:
        return False
    ttl = max(1, int(ttl_seconds))
    try:
        client.setex(namespaced_key(namespace, key), ttl, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
        return True
    except Exception:
        logger.exception("redis_cache_put failed ns=%s key=%s", namespace, key)
        return False


def redis_cache_get(namespace: str, key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(namespaced_key(namespace, key))
    except Exception:
        logger.exception("redis_cache_get failed ns=%s key=%s", namespace, key)
        return None
    if raw is None:
        return None
    try:
        return pickle.loads(raw)
    except Exception:
        logger.exception("redis_cache_get unpickle failed ns=%s key=%s", namespace, key)
        try:
            client.delete(namespaced_key(namespace, key))
        except Exception:
            pass
        return None


def redis_cache_delete(namespace: str, key: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(namespaced_key(namespace, key))
    except Exception:
        logger.exception("redis_cache_delete failed ns=%s key=%s", namespace, key)


def redis_cache_clear_namespace(namespace: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    pattern = namespaced_key(namespace, "*")
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.exception("redis_cache_clear_namespace failed ns=%s", namespace)
