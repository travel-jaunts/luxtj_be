from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    ScheduleFrequencyEnum,
)

if TYPE_CHECKING:
    from luxtj.contexts.marketing.domain.campaign import MarketingCampaign


class MarketingBase(DeclarativeBase):
    pass


class MarketingCampaignRow(MarketingBase):
    __tablename__ = "marketing_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    audience: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    frequency_schedule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_domain(cls, campaign: MarketingCampaign) -> MarketingCampaignRow:
        return cls(
            id=str(campaign.id),
            name=campaign.name,
            description=campaign.description,
            status=campaign.status.value,
            channel=campaign.channel.value,
            audience=list(campaign.audience),
            content=campaign.content,
            start_date=campaign.start_date,
            frequency=campaign.frequency.value,
            frequency_schedule=campaign.frequency_schedule,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            deleted_at=campaign.deleted_at,
        )

    def update_from_domain(self, campaign: MarketingCampaign) -> None:
        self.name = campaign.name
        self.description = campaign.description
        self.status = campaign.status.value
        self.channel = campaign.channel.value
        self.audience = list(campaign.audience)
        self.content = campaign.content
        self.start_date = campaign.start_date
        self.frequency = campaign.frequency.value
        self.frequency_schedule = campaign.frequency_schedule
        self.updated_at = campaign.updated_at
        self.deleted_at = campaign.deleted_at

    def to_domain(self) -> MarketingCampaign:
        from luxtj.contexts.marketing.domain.campaign import MarketingCampaign

        return MarketingCampaign(
            id=UUID(self.id),
            name=self.name,
            description=self.description,
            status=CampaignStatusEnum(self.status),
            channel=CampaignChannelEnum(self.channel),
            audience=list(self.audience),
            content=self.content,
            start_date=self.start_date,
            frequency=ScheduleFrequencyEnum(self.frequency),
            frequency_schedule=self.frequency_schedule,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )
