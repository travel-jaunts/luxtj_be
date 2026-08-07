"""Parallel supplier HTTP client (port of TeenvaCurlMultiHandler).

Providers build HandleDescriptor maps; this client owns I/O, optional
in-memory response cache, and booking_api_request_responses audit writes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Any

import httpx

from luxtj.shared_kernel.infrastructure.http.audit_repository import (
    RequestResponseAuditRepository,
)

_SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "api-key",
        "apikey",
        "x-auth-token",
        "cookie",
        "set-cookie",
    }
)
_SENSITIVE_TOKENS = ("secret", "password", "token", "api-key", "apikey", "auth")


@dataclass(slots=True)
class HandleDescriptor:
    """Outbound call descriptor built by hotel/flight adapters."""

    url: str
    method: str = "GET"
    headers: Mapping[str, str] | None = None
    body: str = ""
    booking_api_id: str | None = None
    cache_key: str | None = None
    remarks: str = ""
    request_format: str = ""
    set_cache: bool = False
    cache_ttl: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = 30.0

    @property
    def request_type(self) -> str:
        return self.remarks


type OnResponse = Callable[[str, str], Awaitable[None] | None]
type ProviderHandles = HandleDescriptor | Sequence[HandleDescriptor]
type HandlesInput = Mapping[str, ProviderHandles]
type ResponseMap = dict[str, str | list[str]]


def is_sensitive_header_name(name: str) -> bool:
    lower = name.lower().strip()
    if lower in _SENSITIVE_HEADER_NAMES:
        return True
    return any(token in lower for token in _SENSITIVE_TOKENS)


def redact_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {
        key: ("***" if is_sensitive_header_name(key) else value) for key, value in headers.items()
    }


def serialize_headers_for_audit(headers: Mapping[str, str] | None) -> str:
    return json.dumps(redact_headers(headers), separators=(",", ":"))


def default_cache_key(url: str, body: str = "") -> str:
    return hashlib.md5(f"{url}|{body}".encode(), usedforsecurity=False).hexdigest()


class InMemoryResponseCache:
    """Process-local TTL cache keyed by md5(url|body) (or explicit cache_key)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at <= time.monotonic():
            del self._store[key]
            return None
        if value is None or value == "":
            return None
        return value

    def set(self, key: str, value: str, ttl: int) -> None:
        if value is None or value == "":
            return
        if ttl <= 0:
            return
        self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._store.clear()


@dataclass(slots=True)
class _PreparedCall:
    provider: str
    index: int | None
    descriptor: HandleDescriptor
    insert_id: str | None
    cached_body: str | None = None


class MultiHttpClient:
    """Async multi-request client with audit + optional response cache."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        audit: RequestResponseAuditRepository | None = None,
        cache: InMemoryResponseCache | None = None,
        default_timeout: float = 60.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.4,
    ) -> None:
        self._client = client
        self._audit = audit
        self._cache = cache if cache is not None else InMemoryResponseCache()
        self._default_timeout = default_timeout
        self._max_retries = max(0, max_retries)
        self._retry_backoff_seconds = retry_backoff_seconds
        self._audit_lock = asyncio.Lock()

    async def execute(self, handles: HandlesInput) -> ResponseMap:
        async with self._client_scope() as client:
            prepared = await self._prepare(handles)
            live = [item for item in prepared if item.cached_body is None]
            if live:
                await asyncio.gather(*(self._send_and_finalize(client, item) for item in live))
            return self._collect_responses(prepared)

    async def stream_execute(self, handles: HandlesInput, on_response: OnResponse) -> None:
        async with self._client_scope() as client:
            prepared = await self._prepare(handles)

            for item in prepared:
                if item.cached_body is not None:
                    await _invoke_on_response(on_response, item.provider, item.cached_body)

            live = [item for item in prepared if item.cached_body is None]
            if not live:
                return

            async def _run(item: _PreparedCall) -> None:
                body = await self._send_and_finalize(client, item)
                await _invoke_on_response(on_response, item.provider, body)

            await asyncio.gather(*(_run(item) for item in live))

    def _client_scope(self) -> _ClientScope:
        return _ClientScope(self._client, self._default_timeout)

    async def _prepare(self, handles: HandlesInput) -> list[_PreparedCall]:
        prepared: list[_PreparedCall] = []
        for provider, value in handles.items():
            descriptors = _normalize_descriptors(value)
            multi = _is_list_handles(value)
            for index, descriptor in enumerate(descriptors):
                item_index = index if multi else None
                cached = self._lookup_cache(descriptor)
                if cached is not None:
                    prepared.append(
                        _PreparedCall(
                            provider=provider,
                            index=item_index,
                            descriptor=descriptor,
                            insert_id=None,
                            cached_body=cached,
                        )
                    )
                    continue

                insert_id = await self._insert_pending(descriptor)
                prepared.append(
                    _PreparedCall(
                        provider=provider,
                        index=item_index,
                        descriptor=descriptor,
                        insert_id=insert_id,
                        cached_body=None,
                    )
                )
        return prepared

    def _lookup_cache(self, descriptor: HandleDescriptor) -> str | None:
        if not descriptor.set_cache or not descriptor.cache_ttl:
            return None
        key = descriptor.cache_key or default_cache_key(descriptor.url, descriptor.body or "")
        return self._cache.get(key)

    async def _insert_pending(self, descriptor: HandleDescriptor) -> str | None:
        if self._audit is None or not descriptor.booking_api_id:
            return None
        async with self._audit_lock:
            insert_id = await self._audit.insert_pending(
                booking_api_id=str(descriptor.booking_api_id),
                request_type=descriptor.request_type,
                request_format=descriptor.request_format or "",
                request_url=descriptor.url,
                request_headers=serialize_headers_for_audit(descriptor.headers),
                request_body=descriptor.body or "",
            )
            commit = getattr(self._audit, "commit", None)
            if callable(commit):
                await commit()
            return insert_id

    async def _send_and_finalize(self, client: httpx.AsyncClient, item: _PreparedCall) -> str:
        body, status_code = await self._send(client, item.descriptor)

        if item.insert_id is not None and self._audit is not None:
            async with self._audit_lock:
                await self._audit.update_response(
                    item.insert_id,
                    response=body,
                    response_status_code=status_code,
                )
                commit = getattr(self._audit, "commit", None)
                if callable(commit):
                    await commit()

        descriptor = item.descriptor
        if descriptor.set_cache and descriptor.cache_ttl:
            key = descriptor.cache_key or default_cache_key(descriptor.url, descriptor.body or "")
            self._cache.set(key, body, descriptor.cache_ttl)

        item.cached_body = body
        return body

    async def _send(
        self, client: httpx.AsyncClient, descriptor: HandleDescriptor
    ) -> tuple[str, int]:
        timeout = descriptor.timeout if descriptor.timeout is not None else self._default_timeout
        headers = dict(descriptor.headers or {})
        content: bytes | None = None
        if descriptor.body:
            content = descriptor.body.encode("utf-8")
        attempts = self._max_retries + 1
        last_status = 0
        for attempt in range(attempts):
            try:
                response = await client.request(
                    method=descriptor.method.upper(),
                    url=descriptor.url,
                    headers=headers,
                    content=content,
                    timeout=timeout,
                )
                status = int(response.status_code)
                if status >= 500 and attempt < attempts - 1:
                    await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                    last_status = status
                    continue
                return response.text, status
            except httpx.HTTPError:
                last_status = 0
                if attempt < attempts - 1:
                    await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                    continue
                return "", last_status
        return "", last_status

    @staticmethod
    def _collect_responses(prepared: list[_PreparedCall]) -> ResponseMap:
        responses: ResponseMap = {}
        for item in prepared:
            body = item.cached_body if item.cached_body is not None else ""
            if item.index is None:
                responses[item.provider] = body
            else:
                bucket = responses.get(item.provider)
                if not isinstance(bucket, list):
                    bucket = []
                    responses[item.provider] = bucket
                while len(bucket) <= item.index:
                    bucket.append("")
                bucket[item.index] = body
        return responses


class _ClientScope:
    def __init__(self, client: httpx.AsyncClient | None, default_timeout: float) -> None:
        self._external = client
        self._default_timeout = default_timeout
        self._owned: httpx.AsyncClient | None = None

    async def __aenter__(self) -> httpx.AsyncClient:
        if self._external is not None:
            return self._external
        self._owned = httpx.AsyncClient(timeout=self._default_timeout)
        return self._owned

    async def __aexit__(self, *args: object) -> None:
        if self._owned is not None:
            await self._owned.aclose()
            self._owned = None


def _is_list_handles(value: ProviderHandles) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, HandleDescriptor))


def _normalize_descriptors(value: ProviderHandles) -> list[HandleDescriptor]:
    if isinstance(value, HandleDescriptor):
        return [value]
    return list(value)


async def _invoke_on_response(on_response: OnResponse, provider: str, body: str) -> None:
    result = on_response(provider, body)
    if isawaitable(result):
        await result
