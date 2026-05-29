from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.shared_kernel.domain.events import BaseDomainEvent
from luxtj.utils import timeutils


class SharedKernelBase(DeclarativeBase):
    pass


class DomainEventOutboxRow(SharedKernelBase):
    __tablename__ = "domain_event_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_event(cls, event: BaseDomainEvent) -> DomainEventOutboxRow:
        return cls(
            id=event.id,
            source=event.source,
            type=event.type,
            subject=event.subject,
            time=event.time,
            payload=event.model_dump(mode="json"),
            created_at=timeutils.datetime_now(),
            published_at=None,
        )
