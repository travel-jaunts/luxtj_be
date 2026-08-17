"""Shared multi-HTTP handler — port of ``TeenvaCurlMultiHandler``.

Lives in ``shared_kernel`` (not under hotel/flight) so every booking sub-module
can reuse it. Each sub-module keeps its **own blender** (e.g. ``HotelBlender``)
which injects this client — matching Laravel:

- shared: ``App\\TeenvaLibraries\\TeenvaCurlMultiHandler``
- hotel: ``App\\TeenvaLibraries\\TeenvaHotel\\TeenvaHotelBlender``

Providers build handle descriptors (dict or :class:`HandleDescriptor`); this
module converts provider dicts, runs parallel HTTP with retries + cache, writes
``booking_api_request_responses``, and supports JSON and XML/SOAP bodies.

Import from the package root::

    from luxtj.shared_kernel.infrastructure.http import MultiHttpClient, HandleDescriptor
"""

from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from inspect import isawaitable
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
    MultiHttpTransport,
)

_SHARED_CACHE = InMemoryResponseCache()

_VALID_FORMATS = frozenset({"json", "xml", "soap", "html", "text", "form"})

_CONTENT_TYPE_BY_FORMAT: dict[str, str] = {
    "json": "application/json; charset=utf-8",
    "xml": "application/xml; charset=utf-8",
    "soap": "application/soap+xml; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "text": "text/plain; charset=utf-8",
    "form": "application/x-www-form-urlencoded; charset=utf-8",
}

_ACCEPT_BY_FORMAT: dict[str, str] = {
    "json": "application/json",
    "xml": "application/xml, text/xml, */*",
    "soap": "application/soap+xml, application/xml, text/xml, */*",
    "html": "text/html, */*",
    "text": "text/plain, */*",
    "form": "*/*",
}


def _header_get(headers: Mapping[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def _header_has(headers: Mapping[str, str], name: str) -> bool:
    return _header_get(headers, name) is not None


def _format_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    lower = content_type.lower()
    if "soap+xml" in lower or "soap" in lower:
        return "soap"
    if "json" in lower:
        return "json"
    if "xml" in lower:
        return "xml"
    if "html" in lower:
        return "html"
    if "x-www-form-urlencoded" in lower:
        return "form"
    if "text/plain" in lower:
        return "text"
    return None


def _sniff_body_format(body: str) -> str | None:
    sample = body.lstrip("\ufeff \t\r\n")
    if not sample:
        return None
    if sample[0] in "{[":
        return "json"
    if sample.startswith("<?xml") or sample.startswith("<"):
        lower = sample[:200].lower()
        if "soap" in lower or "envelope" in lower:
            return "soap"
        return "xml"
    return None


def normalize_request_format(
    *,
    explicit: Any,
    headers: Mapping[str, str],
    body: str,
) -> str:
    """Resolve request format from explicit value, Content-Type, or body sniff."""
    if explicit is not None and str(explicit).strip():
        candidate = str(explicit).strip().lower()
        if candidate in _VALID_FORMATS:
            return candidate
        from_alias = _format_from_content_type(candidate)
        if from_alias:
            return from_alias

    from_header = _format_from_content_type(_header_get(headers, "Content-Type"))
    if from_header:
        return from_header

    sniffed = _sniff_body_format(body)
    if sniffed:
        return sniffed

    return "json"


def serialize_request_body(body: Any, request_format: str) -> str:
    """Serialize outbound body for JSON or XML/SOAP/text formats."""
    if body is None:
        return ""
    if isinstance(body, (bytes, bytearray, memoryview)):
        return bytes(body).decode("utf-8")
    if isinstance(body, (dict, list)):
        if request_format in {"xml", "soap"}:
            raise ValueError(
                f"XML/SOAP request body must be a pre-serialized string; got {type(body).__name__}"
            )
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    if isinstance(body, str):
        return body
    return str(body)


def ensure_format_headers(headers: dict[str, str], request_format: str) -> dict[str, str]:
    """Add Content-Type / Accept for the format when the caller did not set them."""
    out = dict(headers)
    content_type = _CONTENT_TYPE_BY_FORMAT.get(request_format)
    accept = _ACCEPT_BY_FORMAT.get(request_format)
    if content_type and not _header_has(out, "Content-Type"):
        out["Content-Type"] = content_type
    if accept and not _header_has(out, "Accept"):
        out["Accept"] = accept
    return out


def detect_response_format(body: str, content_type: str | None = None) -> str:
    """Best-effort response format detection (json | xml | soap | html | text)."""
    from_header = _format_from_content_type(content_type)
    if from_header:
        return from_header
    sniffed = _sniff_body_format(body)
    if sniffed:
        return sniffed
    return "text"


def parse_response_body(
    body: str,
    *,
    content_type: str | None = None,
    preferred_format: str | None = None,
) -> Any:
    """Parse a response body as JSON object/list or return raw XML/text string.

    - JSON → decoded Python object
    - XML / SOAP / HTML / text → original string (callers parse XML themselves)
    """
    if body is None:
        return ""
    text = body if isinstance(body, str) else str(body)
    fmt = (preferred_format or "").strip().lower()
    if fmt not in _VALID_FORMATS:
        fmt = detect_response_format(text, content_type)

    if fmt == "json":
        stripped = text.strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return text

    return text


def normalize_response_text(body: str) -> str:
    """Normalize response text for both JSON and XML (BOM strip, keep payload intact)."""
    if not body:
        return ""
    if body.startswith("\ufeff"):
        body = body.lstrip("\ufeff")
    return body


def dict_handle_to_descriptor(handle: Mapping[str, Any] | HandleDescriptor) -> HandleDescriptor:
    """Convert a provider handle dict (or descriptor) into a :class:`HandleDescriptor`."""
    if isinstance(handle, HandleDescriptor):
        headers = ensure_format_headers(
            dict(handle.headers or {}),
            (handle.request_format or "json").lower() or "json",
        )
        return HandleDescriptor(
            url=handle.url,
            method=handle.method,
            headers=headers,
            body=handle.body,
            booking_api_id=handle.booking_api_id,
            cache_key=handle.cache_key,
            remarks=handle.remarks,
            request_format=handle.request_format or "json",
            set_cache=handle.set_cache,
            cache_ttl=handle.cache_ttl,
            meta=dict(handle.meta or {}),
            timeout=handle.timeout,
        )

    headers_raw = handle.get("headers") or handle.get("requestHeaders") or []
    header_map: dict[str, str] = {}
    if isinstance(headers_raw, Mapping):
        header_map = {str(k): str(v) for k, v in headers_raw.items()}
    elif isinstance(headers_raw, str):
        try:
            parsed = json.loads(headers_raw)
            if isinstance(parsed, Mapping):
                header_map = {str(k): str(v) for k, v in parsed.items()}
            elif isinstance(parsed, list):
                headers_raw = parsed
        except json.JSONDecodeError:
            headers_raw = [headers_raw]
    if (
        not header_map
        and isinstance(headers_raw, Sequence)
        and not isinstance(headers_raw, (str, bytes))
    ):
        for h in headers_raw:
            if not isinstance(h, str) or ":" not in h:
                continue
            key, value = h.split(":", 1)
            header_map[key.strip()] = value.strip()

    raw_body = handle.get("requestBody")
    if raw_body is None:
        raw_body = handle.get("body")
    if raw_body is None:
        raw_body = ""

    sniff_sample = ""
    if isinstance(raw_body, str):
        sniff_sample = raw_body
    elif isinstance(raw_body, (bytes, bytearray, memoryview)):
        sniff_sample = bytes(raw_body).decode("utf-8", errors="replace")

    request_format = normalize_request_format(
        explicit=handle.get("request_format") or handle.get("requestFormat"),
        headers=header_map,
        body=sniff_sample,
    )
    body = serialize_request_body(raw_body, request_format)
    if not (handle.get("request_format") or handle.get("requestFormat")):
        request_format = normalize_request_format(
            explicit=None,
            headers=header_map,
            body=body,
        )

    header_map = ensure_format_headers(header_map, request_format)

    booking_api_id = handle.get("bookingApiId") or handle.get("booking_api_id")
    timeout = handle.get("timeout")
    cache_ttl = handle.get("cache_ttl") or handle.get("cacheTtl")
    set_cache = bool(handle.get("set_cache") or handle.get("setCache") or cache_ttl)
    remarks = str(handle.get("remarks") or handle.get("request_type") or "")
    meta = dict(handle.get("meta") or {})
    if "response_format" in handle or "responseFormat" in handle:
        meta["response_format"] = str(
            handle.get("response_format") or handle.get("responseFormat") or ""
        )

    return HandleDescriptor(
        url=str(handle.get("url") or ""),
        method=str(handle.get("method") or "POST"),
        headers=header_map,
        body=body,
        booking_api_id=str(booking_api_id) if booking_api_id else None,
        cache_key=handle.get("cache_key") or handle.get("cacheKey"),
        remarks=remarks,
        request_format=request_format,
        set_cache=set_cache,
        cache_ttl=int(cache_ttl) if cache_ttl else None,
        meta=meta,
        timeout=float(timeout) if timeout is not None else 60.0,
    )


def _normalize_provider_handles(
    value: HandleDescriptor | Mapping[str, Any] | Sequence[Any],
) -> list[HandleDescriptor]:
    if isinstance(value, HandleDescriptor):
        return [dict_handle_to_descriptor(value)]
    if isinstance(value, Mapping):
        return [dict_handle_to_descriptor(value)]
    return [dict_handle_to_descriptor(item) for item in value]


async def _maybe_await(result: Any) -> None:
    if isawaitable(result):
        await result


class MultiHttpClient:
    """Public multi-HTTP API for all booking sub-modules (hotel, flight, …).

    Mirrors ``TeenvaCurlMultiHandler``: accept named provider handle maps, execute
    in parallel, audit to DB, optionally cache, and stream or collect raw bodies.
    """

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
        self._core = MultiHttpTransport(
            client=client,
            audit=audit,
            cache=_SHARED_CACHE,
            default_timeout=float(getattr(config, "HTTP_DEFAULT_TIMEOUT", default_timeout)),
            max_retries=int(getattr(config, "HTTP_MAX_RETRIES", max_retries)),
        )

    async def stream_execute(
        self,
        named_handles: dict[str, Any],
        on_complete: Callable[[str, str], Awaitable[None] | None],
    ) -> None:
        converted: dict[str, list[HandleDescriptor]] = {}
        for provider, handles in named_handles.items():
            converted[provider] = _normalize_provider_handles(handles)

        async def _on_response(provider: str, body: str) -> None:
            await _maybe_await(on_complete(provider, normalize_response_text(body)))

        await self._core.stream_execute(converted, _on_response)

    async def execute(self, named_handles: dict[str, Any]) -> dict[str, str | list[str]]:
        converted: dict[str, list[HandleDescriptor]] = {}
        for provider, handles in named_handles.items():
            converted[provider] = _normalize_provider_handles(handles)
        raw = await self._core.execute(converted)
        normalized: dict[str, str | list[str]] = {}
        for key, value in raw.items():
            if isinstance(value, list):
                normalized[key] = [normalize_response_text(item) for item in value]
            else:
                normalized[key] = normalize_response_text(value)
        return normalized


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
