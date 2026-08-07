"""Hotel multi-HTTP adapter — ports TeenvaCurlMultiHandler usage onto shared MultiHttpClient.

Accepts RateHawk-style dict handles and converts them to HandleDescriptor so search
gets parallel I/O, retries, cache, and booking_api_request_responses audit rows.
"""

from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

import httpx

from luxtj.bootstrap import config
from luxtj.shared_kernel.infrastructure.http.audit_repository import (
    RequestResponseAuditRepository,
    SqlAlchemyRequestResponseAuditRepository,
)
from luxtj.shared_kernel.infrastructure.http.multi_http_client import (
    HandleDescriptor,
    InMemoryResponseCache,
    MultiHttpClient as SharedMultiHttpClient,
)

_SHARED_CACHE = InMemoryResponseCache()


def dict_handle_to_descriptor(handle: Mapping[str, Any] | HandleDescriptor) -> HandleDescriptor:
    if isinstance(handle, HandleDescriptor):
        return handle

    headers_raw = handle.get("headers") or []
    header_map: dict[str, str] = {}
    if isinstance(headers_raw, Mapping):
        header_map = {str(k): str(v) for k, v in headers_raw.items()}
    else:
        for h in headers_raw:
            if not isinstance(h, str) or ":" not in h:
                continue
            key, value = h.split(":", 1)
            header_map[key.strip()] = value.strip()

    body = handle.get("requestBody")
    if body is None:
        body = handle.get("body") or ""
    if not isinstance(body, str):
        body = str(body)

    booking_api_id = handle.get("bookingApiId") or handle.get("booking_api_id")
    timeout = handle.get("timeout")
    cache_ttl = handle.get("cache_ttl") or handle.get("cacheTtl")
    set_cache = bool(handle.get("set_cache") or handle.get("setCache") or cache_ttl)
    remarks = str(handle.get("remarks") or handle.get("request_type") or "")

    return HandleDescriptor(
        url=str(handle.get("url") or ""),
        method=str(handle.get("method") or "POST"),
        headers=header_map,
        body=body,
        booking_api_id=str(booking_api_id) if booking_api_id else None,
        cache_key=handle.get("cache_key") or handle.get("cacheKey"),
        remarks=remarks,
        request_format=str(handle.get("request_format") or handle.get("requestFormat") or "json"),
        set_cache=set_cache,
        cache_ttl=int(cache_ttl) if cache_ttl else None,
        meta=dict(handle.get("meta") or {}),
        timeout=float(timeout) if timeout is not None else 60.0,
    )


def _normalize_provider_handles(
    value: HandleDescriptor | Mapping[str, Any] | Sequence[Any],
) -> list[HandleDescriptor]:
    if isinstance(value, HandleDescriptor):
        return [value]
    if isinstance(value, Mapping):
        return [dict_handle_to_descriptor(value)]
    return [dict_handle_to_descriptor(item) for item in value]


class MultiHttpClient:
    """Back-compat wrapper used by HotelBlender.stream_execute(dict handles)."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        audit: RequestResponseAuditRepository | None = None,
        session: Any | None = None,
        default_timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        if audit is None and session is not None:
            audit = SqlAlchemyRequestResponseAuditRepository(session)
        self._shared = SharedMultiHttpClient(
            client=client,
            audit=audit,
            cache=_SHARED_CACHE,
            default_timeout=float(getattr(config, "HTTP_DEFAULT_TIMEOUT", 60.0)),
            max_retries=int(getattr(config, "HTTP_MAX_RETRIES", 2)),
        )

    async def stream_execute(
        self,
        named_handles: dict[str, Any],
        on_complete: Callable[[str, str], Awaitable[None] | None],
    ) -> None:
        converted: dict[str, list[HandleDescriptor]] = {}
        for provider, handles in named_handles.items():
            converted[provider] = _normalize_provider_handles(handles)
        await self._shared.stream_execute(converted, on_complete)

    async def execute(self, named_handles: dict[str, Any]) -> dict[str, str | list[str]]:
        converted: dict[str, list[HandleDescriptor]] = {}
        for provider, handles in named_handles.items():
            converted[provider] = _normalize_provider_handles(handles)
        return await self._shared.execute(converted)


# Re-export for callers that need Basic auth decode helpers (legacy)
def decode_basic_auth_header(value: str) -> tuple[str, str] | None:
    if not value.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(value.split(" ", 1)[1]).decode()
        if ":" not in decoded:
            return None
        user, password = decoded.split(":", 1)
        return user, password
    except Exception:
        return None
