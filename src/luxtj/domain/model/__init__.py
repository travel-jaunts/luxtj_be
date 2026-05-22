from datetime import date, datetime
from uuid import UUID, uuid7

from sqlalchemy import Date, String, Text, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.domain.enums import CampaignChannelEnum, ScheduleFrequencyEnum
from luxtj.utils import timeutils


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        Date, nullable=False, default=timeutils.datetime_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        Date, nullable=False, default=timeutils.datetime_now, onupdate=timeutils.datetime_now
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(Date, nullable=True, default=None)


class MarketingCampaign(Base, TimestampMixin, SoftDeleteMixin):
    """Entity mapped to a PostgreSQL table for campaign data captured by marketing DTOs."""

    __tablename__ = "marketing_campaigns"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[CampaignChannelEnum] = mapped_column(String(64), nullable=False)
    audience: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    frequency: Mapped[ScheduleFrequencyEnum] = mapped_column(String(32), nullable=False)
    frequency_schedule: Mapped[str | None] = mapped_column(String(255), nullable=True)
