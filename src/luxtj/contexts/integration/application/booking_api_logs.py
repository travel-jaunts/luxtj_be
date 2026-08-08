"""Admin queries for booking_api_request_responses audit logs."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_models import (
    BookingApiRow,
    SubModuleRow,
)
from luxtj.shared_kernel.infrastructure.http import BookingApiRequestResponseRow

DownloadPart = Literal["request", "response", "headers"]


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _day_end(d: date) -> datetime:
    return datetime.combine(d, time.max, tzinfo=timezone.utc)


def _truncate(value: str | None, limit: int = 240) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def permission_codes_for_api(*, sub_module: str, api_code: str) -> tuple[str, ...]:
    """Any of these grants access to logs for this booking API."""
    sub = sub_module.strip().lower()
    code = api_code.strip().lower()
    return (
        f"booking_api_logs.{sub}.{code}.view",
        f"booking_api_logs.{sub}.view",
        "booking_api_logs.view",
    )


def _sniff_format(body: str | None, fallback: str = "txt") -> str:
    sample = (body or "").lstrip("\ufeff \t\r\n")
    if not sample:
        return fallback or "txt"
    if sample[0] in "{[":
        return "json"
    if sample.startswith("<?xml") or sample.startswith("<"):
        lower = sample[:200].lower()
        if "soap" in lower or "envelope" in lower:
            return "xml"
        return "xml"
    fmt = (fallback or "").strip().lower()
    if fmt in {"json", "xml", "soap"}:
        return "xml" if fmt == "soap" else fmt
    return "txt"


def _extension_for_format(fmt: str) -> str:
    if fmt == "json":
        return "json"
    if fmt in {"xml", "soap"}:
        return "xml"
    return "txt"


def _media_type_for_format(fmt: str) -> str:
    if fmt == "json":
        return "application/json"
    if fmt in {"xml", "soap"}:
        return "application/xml"
    return "text/plain"


def _headers_as_text(raw: str | None) -> str:
    if not raw:
        return ""
    text = raw.strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, dict):
        lines = [f"{k}: {v}" for k, v in parsed.items()]
        return "\n".join(lines)
    if isinstance(parsed, list):
        return "\n".join(str(item) for item in parsed)
    return text


class BookingApiLogsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_booking_api(
        self,
        *,
        booking_api_id: str | None = None,
        booking_api_code: str | None = None,
        sub_module: str | None = None,
    ) -> dict[str, str] | None:
        """Return {id, code, name, subModule} or None."""
        if booking_api_id:
            stmt = (
                select(BookingApiRow, SubModuleRow.name)
                .join(SubModuleRow, SubModuleRow.id == BookingApiRow.sub_module_id)
                .where(BookingApiRow.id == booking_api_id)
            )
            row = (await self._session.execute(stmt)).first()
            if row is None:
                return None
            api, sub_name = row
            return {
                "id": api.id,
                "code": api.code,
                "name": api.name,
                "subModule": sub_name,
            }

        if booking_api_code and sub_module:
            stmt = (
                select(BookingApiRow, SubModuleRow.name)
                .join(SubModuleRow, SubModuleRow.id == BookingApiRow.sub_module_id)
                .where(
                    BookingApiRow.code == booking_api_code.strip().lower(),
                    func.lower(SubModuleRow.name) == sub_module.strip().lower(),
                )
            )
            row = (await self._session.execute(stmt)).first()
            if row is None:
                return None
            api, sub_name = row
            return {
                "id": api.id,
                "code": api.code,
                "name": api.name,
                "subModule": sub_name,
            }
        return None

    async def list_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        booking_api_id: str | None = None,
        booking_api_code: str | None = None,
        sub_module: str | None = None,
        request_type: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        resolved = await self.resolve_booking_api(
            booking_api_id=booking_api_id,
            booking_api_code=booking_api_code,
            sub_module=sub_module,
        )
        if not resolved:
            return {
                "items": [],
                "page": page,
                "pageSize": page_size,
                "total": 0,
                "hasMore": False,
                "bookingApi": None,
            }

        filters = [
            BookingApiRequestResponseRow.booking_api_id == resolved["id"],
        ]
        if request_type and request_type.strip():
            filters.append(
                BookingApiRequestResponseRow.request_type.ilike(f"%{request_type.strip()}%")
            )
        if from_date:
            filters.append(BookingApiRequestResponseRow.created_at >= _day_start(from_date))
        if to_date:
            filters.append(BookingApiRequestResponseRow.created_at <= _day_end(to_date))

        count_stmt = (
            select(func.count())
            .select_from(BookingApiRequestResponseRow)
            .where(*filters)
        )
        total = int((await self._session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(BookingApiRequestResponseRow)
            .where(*filters)
            .order_by(BookingApiRequestResponseRow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        items = [
            {
                "id": row.id,
                "bookingApiId": row.booking_api_id,
                "bookingApiCode": resolved["code"],
                "bookingApiName": resolved["name"],
                "subModule": resolved["subModule"],
                "requestType": row.request_type,
                "requestFormat": row.request_format,
                "requestUrl": row.request_url,
                "requestUrlPreview": _truncate(row.request_url, 120),
                "responseStatusCode": row.response_status_code,
                "hasResponse": bool(row.response),
                "hasRequestBody": bool(row.request_body),
                "hasRequestHeaders": bool(row.request_headers),
                "createdAt": row.created_at.isoformat() if row.created_at else None,
                "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
        return {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "total": total,
            "hasMore": page * page_size < total,
            "bookingApi": resolved,
        }

    async def get_log(self, log_id: str) -> dict[str, Any] | None:
        stmt = (
            select(BookingApiRequestResponseRow, BookingApiRow, SubModuleRow.name)
            .outerjoin(
                BookingApiRow,
                BookingApiRow.id == BookingApiRequestResponseRow.booking_api_id,
            )
            .outerjoin(SubModuleRow, SubModuleRow.id == BookingApiRow.sub_module_id)
            .where(BookingApiRequestResponseRow.id == log_id)
        )
        result = (await self._session.execute(stmt)).first()
        if result is None:
            return None
        row, api, sub_name = result
        return {
            "id": row.id,
            "bookingApiId": row.booking_api_id,
            "bookingApiCode": api.code if api else None,
            "bookingApiName": api.name if api else None,
            "subModule": sub_name,
            "requestType": row.request_type,
            "requestFormat": row.request_format,
            "requestUrl": row.request_url,
            "requestHeaders": row.request_headers,
            "requestBody": row.request_body,
            "response": row.response,
            "responseStatusCode": row.response_status_code,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def download_part(
        self, log_id: str, part: DownloadPart
    ) -> dict[str, Any] | None:
        """Return {content, filename, mediaType} for request | response | headers."""
        detail = await self.get_log(log_id)
        if detail is None:
            return None

        api_code = str(detail.get("bookingApiCode") or "api")
        req_fmt = str(detail.get("requestFormat") or "")

        if part == "headers":
            content = _headers_as_text(detail.get("requestHeaders"))
            return {
                "content": content,
                "filename": f"{api_code}-{log_id}-headers.txt",
                "mediaType": "text/plain; charset=utf-8",
            }

        if part == "request":
            body = detail.get("requestBody") or ""
            fmt = _sniff_format(body if isinstance(body, str) else str(body), req_fmt or "txt")
            ext = _extension_for_format(fmt)
            return {
                "content": body if isinstance(body, str) else str(body),
                "filename": f"{api_code}-{log_id}-request.{ext}",
                "mediaType": f"{_media_type_for_format(fmt)}; charset=utf-8",
            }

        # response
        body = detail.get("response") or ""
        fmt = _sniff_format(body if isinstance(body, str) else str(body), req_fmt or "txt")
        ext = _extension_for_format(fmt)
        return {
            "content": body if isinstance(body, str) else str(body),
            "filename": f"{api_code}-{log_id}-response.{ext}",
            "mediaType": f"{_media_type_for_format(fmt)}; charset=utf-8",
        }
