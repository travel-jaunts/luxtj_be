"""Audit repository: insert pending supplier request, update when complete."""

from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.shared_kernel.infrastructure.http.audit_body import compress_audit_body
from luxtj.shared_kernel.infrastructure.http.audit_models import BookingApiRequestResponseRow
from luxtj.utils import timeutils


class RequestResponseAuditRepository(Protocol):
    async def insert_pending(
        self,
        *,
        booking_api_id: str,
        request_type: str,
        request_format: str,
        request_url: str,
        request_headers: str | None,
        request_body: str | None,
    ) -> str: ...

    async def update_response(
        self,
        insert_id: str,
        *,
        response: str,
        response_status_code: int,
        now: datetime | None = None,
    ) -> None: ...

    async def commit(self) -> None: ...


class SqlAlchemyRequestResponseAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_pending(
        self,
        *,
        booking_api_id: str,
        request_type: str,
        request_format: str,
        request_url: str,
        request_headers: str | None,
        request_body: str | None,
    ) -> str:
        row = BookingApiRequestResponseRow.pending(
            booking_api_id=booking_api_id,
            request_type=request_type,
            request_format=request_format,
            request_url=request_url,
            request_headers=request_headers,
            request_body=compress_audit_body(
                request_body, request_format=request_format
            ),
        )
        self._session.add(row)
        await self._session.flush()
        return str(row.id)

    async def update_response(
        self,
        insert_id: str,
        *,
        response: str,
        response_status_code: int,
        now: datetime | None = None,
    ) -> None:
        row = await self._session.get(BookingApiRequestResponseRow, str(insert_id))
        if row is None:
            return
        row.response = compress_audit_body(
            response, request_format=row.request_format
        )
        row.response_status_code = response_status_code
        row.updated_at = now or timeutils.datetime_now()
        await self._session.flush()

    async def commit(self) -> None:
        """Persist audit rows mid-stream so logs survive client disconnects."""
        await self._session.commit()
