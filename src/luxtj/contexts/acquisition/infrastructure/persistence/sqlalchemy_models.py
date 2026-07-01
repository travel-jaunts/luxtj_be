from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.acquisition.domain.enums import WaitlistStatus
from luxtj.contexts.acquisition.domain.value_objects import AcquisitionContext, Email
from luxtj.contexts.acquisition.domain.waitlist_entry import WaitlistEntry


class AcquisitionBase(DeclarativeBase):
    pass


class WaitlistEntryRow(AcquisitionBase):
    __tablename__ = "acquisition_waitlist_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    referral_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acquisition_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, entry: WaitlistEntry) -> WaitlistEntryRow:
        return cls(
            id=str(entry.id),
            name=entry.name,
            email=entry.email.value,
            status=entry.status.value,
            source=entry.source,
            referral_code=entry.referral_code,
            acquisition_context=entry.acquisition_context.to_dict(),
            registered_at=entry.registered_at,
        )

    def to_domain(self) -> WaitlistEntry:
        from luxtj.contexts.acquisition.domain.waitlist_entry import WaitlistEntry

        return WaitlistEntry(
            id=UUID(self.id),
            name=self.name,
            email=Email(self.email),
            status=WaitlistStatus(self.status),
            source=self.source,
            referral_code=self.referral_code,
            acquisition_context=AcquisitionContext(
                ip_address=self.acquisition_context.get("ip_address"),
                user_agent=self.acquisition_context.get("user_agent"),
                referer=self.acquisition_context.get("referer"),
                accept_language=self.acquisition_context.get("accept_language"),
                utm_source=self.acquisition_context.get("utm_source"),
                utm_medium=self.acquisition_context.get("utm_medium"),
                utm_campaign=self.acquisition_context.get("utm_campaign"),
                utm_term=self.acquisition_context.get("utm_term"),
                utm_content=self.acquisition_context.get("utm_content"),
            ),
            registered_at=self.registered_at,
        )
