"""SQLAlchemy model for supplier HTTP audit rows.

Matches architecture-curl-multi-handler.md and migration
`20260807_hotel_crs_booking_core` (`booking_api_request_responses`).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from luxtj.shared_kernel.infrastructure.persistence.outbox_model import SharedKernelBase
from luxtj.utils import timeutils


class BookingApiRequestResponseRow(SharedKernelBase):
    __tablename__ = "booking_api_request_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    booking_api_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    request_format: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    request_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    request_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_status_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def pending(
        cls,
        *,
        booking_api_id: str,
        request_type: str,
        request_format: str,
        request_url: str,
        request_headers: str | None,
        request_body: str | None,
        now: datetime | None = None,
    ) -> "BookingApiRequestResponseRow":
        ts = now or timeutils.datetime_now()
        return cls(
            id=str(uuid4()),
            booking_api_id=booking_api_id,
            request_type=request_type,
            request_format=request_format,
            request_url=request_url,
            request_headers=request_headers,
            request_body=request_body,
            response="",
            response_status_code=None,
            created_at=ts,
            updated_at=ts,
        )
