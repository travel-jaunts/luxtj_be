from typing import Dict
from asyncio import Lock as CoroutineLock

from fastapi import FastAPI
from httpx import AsyncClient

from app.core.bases import SingletonMeta, IAsyncCachingProvider


async def get_http_client(app: FastAPI) -> AsyncClient:
    """Dependency injector for httpx AsyncClient instance stored in app state"""
    return app.state.http_client


class InProcessAsyncCacheSingletonMeta(SingletonMeta, type(IAsyncCachingProvider)):
    pass


class InProcessAsyncCache(metaclass=InProcessAsyncCacheSingletonMeta):
    """A simple in-process async caching provider implementation for demonstration purposes.
    Note: This is not suitable for production use due to lack of persistence and potential memory leaks.
    """

    def __init__(self):
        self._cache_operaton_lock: CoroutineLock = CoroutineLock()
        self._cache: Dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        async with self._cache_operaton_lock:
            return self._cache.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 0) -> None:
        async with self._cache_operaton_lock:
            self._cache[key] = value
        # TTL handling is omitted for simplicity

    async def delete(self, key: str) -> None:
        async with self._cache_operaton_lock:
            if key in self._cache:
                del self._cache[key]
