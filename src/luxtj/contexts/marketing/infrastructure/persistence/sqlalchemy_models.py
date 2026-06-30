from datetime import date, datetime
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
from luxtj.contexts.marketing.domain.enums import (
    CampaignChannelEnum,
    CampaignStatusEnum,
    OfferStatusEnum,
    OfferTypeEnum,
    ScheduleFrequencyEnum,
)
from luxtj.contexts.marketing.domain.offer import Offer


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


class MarketingOfferRow(MarketingBase):
    __tablename__ = "marketing_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    discount_value: Mapped[float] = mapped_column(Float, nullable=False)
    min_booking_value: Mapped[float] = mapped_column(Float, nullable=False)
    min_booking_value_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    validity_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validity_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usage_limit_per_user: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicability_on: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    stackable: Mapped[bool] = mapped_column(nullable=False, default=False)
    auto_apply: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_domain(cls, offer: Offer) -> MarketingOfferRow:
        return cls(
            id=str(offer.id),
            name=offer.name,
            code=offer.code,
            type=offer.type.value,
            discount_value=offer.discount_value,
            min_booking_value=offer.min_booking_value,
            min_booking_value_currency=offer.min_booking_value_currency,
            validity_start=offer.validity_start,
            validity_end=offer.validity_end,
            usage_limit_per_user=offer.usage_limit_per_user,
            applicability_on=list(offer.applicability_on),
            stackable=offer.stackable,
            auto_apply=offer.auto_apply,
            status=offer.status.value,
            created_at=offer.created_at,
            updated_at=offer.updated_at,
            deleted_at=offer.deleted_at,
        )

    def update_from_domain(self, offer: Offer) -> None:
        self.name = offer.name
        self.discount_value = offer.discount_value
        self.min_booking_value = offer.min_booking_value
        self.min_booking_value_currency = offer.min_booking_value_currency
        self.validity_start = offer.validity_start
        self.validity_end = offer.validity_end
        self.usage_limit_per_user = offer.usage_limit_per_user
        self.applicability_on = list(offer.applicability_on)
        self.stackable = offer.stackable
        self.auto_apply = offer.auto_apply
        self.status = offer.status.value
        self.updated_at = offer.updated_at
        self.deleted_at = offer.deleted_at

    def to_domain(self) -> Offer:
        from luxtj.contexts.marketing.domain.offer import Offer

        return Offer(
            id=UUID(self.id),
            name=self.name,
            code=self.code,
            type=OfferTypeEnum(self.type),
            discount_value=self.discount_value,
            min_booking_value=self.min_booking_value,
            min_booking_value_currency=self.min_booking_value_currency,
            validity_start=self.validity_start,
            validity_end=self.validity_end,
            usage_limit_per_user=self.usage_limit_per_user,
            applicability_on=list(self.applicability_on),
            stackable=self.stackable,
            auto_apply=self.auto_apply,
            status=OfferStatusEnum(self.status),
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )
