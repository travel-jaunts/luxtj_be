"""Admin queries for booking_api_request_responses audit logs."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_models import (
    BookingApiRow,
)
from luxtj.shared_kernel.infrastructure.http.audit_models import BookingApiRequestResponseRow


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


class BookingApiLogsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        booking_api_id: str | None = None,
        request_type: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        filters = []
        if booking_api_id:
            filters.append(BookingApiRequestResponseRow.booking_api_id == booking_api_id)
        if request_type:
            filters.append(BookingApiRequestResponseRow.request_type.ilike(f"%{request_type}%"))
        if from_date:
            filters.append(BookingApiRequestResponseRow.created_at >= _day_start(from_date))
        if to_date:
            filters.append(BookingApiRequestResponseRow.created_at <= _day_end(to_date))
        if q:
            like = f"%{q.strip()}%"
            filters.append(
                or_(
                    BookingApiRequestResponseRow.request_url.ilike(like),
                    BookingApiRequestResponseRow.request_type.ilike(like),
                )
            )

        count_stmt = select(func.count()).select_from(BookingApiRequestResponseRow)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await self._session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(BookingApiRequestResponseRow, BookingApiRow.code, BookingApiRow.name)
            .outerjoin(
                BookingApiRow,
                BookingApiRow.id == BookingApiRequestResponseRow.booking_api_id,
            )
            .order_by(BookingApiRequestResponseRow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if filters:
            stmt = stmt.where(*filters)

        rows = (await self._session.execute(stmt)).all()
        items = [
            {
                "id": row.id,
                "bookingApiId": row.booking_api_id,
                "bookingApiCode": api_code,
                "bookingApiName": api_name,
                "requestType": row.request_type,
                "requestFormat": row.request_format,
                "requestUrl": row.request_url,
                "requestUrlPreview": _truncate(row.request_url, 120),
                "responseStatusCode": row.response_status_code,
                "hasResponse": bool(row.response),
                "createdAt": row.created_at.isoformat() if row.created_at else None,
                "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row, api_code, api_name in rows
        ]
        return {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "total": total,
            "hasMore": page * page_size < total,
        }

    async def get_log(self, log_id: str) -> dict[str, Any] | None:
        stmt = (
            select(BookingApiRequestResponseRow, BookingApiRow.code, BookingApiRow.name)
            .outerjoin(
                BookingApiRow,
                BookingApiRow.id == BookingApiRequestResponseRow.booking_api_id,
            )
            .where(BookingApiRequestResponseRow.id == log_id)
        )
        result = (await self._session.execute(stmt)).first()
        if result is None:
            return None
        row, api_code, api_name = result
        return {
            "id": row.id,
            "bookingApiId": row.booking_api_id,
            "bookingApiCode": api_code,
            "bookingApiName": api_name,
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

    async def download_payload(self, log_id: str) -> dict[str, Any] | None:
        detail = await self.get_log(log_id)
        if detail is None:
            return None
        return {
            "id": detail["id"],
            "booking_api_id": detail["bookingApiId"],
            "booking_api_code": detail.get("bookingApiCode"),
            "booking_api_name": detail.get("bookingApiName"),
            "request_type": detail["requestType"],
            "request_format": detail["requestFormat"],
            "request_url": detail["requestUrl"],
            "request_headers": detail.get("requestHeaders"),
            "request_body": detail.get("requestBody"),
            "response_status_code": detail.get("responseStatusCode"),
            "response": detail.get("response"),
            "created_at": detail.get("createdAt"),
            "updated_at": detail.get("updatedAt"),
        }
