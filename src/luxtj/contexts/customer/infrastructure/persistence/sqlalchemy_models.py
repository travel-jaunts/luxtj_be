import json
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.customer.domain.bucket_list import BucketList, BucketListItem
from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    BucketDestinationKindEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
from luxtj.contexts.customer.domain.personal_calendar import (
    PersonalCalendar,
    PersonalCalendarEventItem,
    PersonalCalendarPeriodItem,
)


class CustomerBase(DeclarativeBase):
    pass


class CustomerBucketListRow(CustomerBase):
    __tablename__ = "customer_bucket_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, bucket_list: BucketList) -> CustomerBucketListRow:
        return cls(
            id=str(bucket_list.id),
            account_id=str(bucket_list.account_id),
            created_at=bucket_list.created_at,
            updated_at=bucket_list.updated_at,
        )

    def update_from_domain(self, bucket_list: BucketList) -> None:
        self.updated_at = bucket_list.updated_at

    def to_domain(self, items: list[BucketListItem]) -> BucketList:
        return BucketList(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            items=items,
        )


class CustomerBucketListItemRow(CustomerBase):
    __tablename__ = "customer_bucket_list_items"
    __table_args__ = (
        UniqueConstraint(
            "bucket_list_id",
            "destination_kind",
            "normalized_destination_name",
            "is_active",
            name="uq_customer_bucket_active_destination",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bucket_list_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customer_bucket_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ideal_days: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_domain(
        cls,
        *,
        bucket_list_id: UUID,
        item: BucketListItem,
    ) -> CustomerBucketListItemRow:
        return cls(
            id=str(item.id),
            bucket_list_id=str(bucket_list_id),
            destination_kind=item.destination_kind.value,
            destination_name=item.destination_name,
            normalized_destination_name=item.normalized_destination_name,
            parent_country=item.parent_country,
            ideal_days=item.ideal_days,
            display_order=item.display_order,
            notes=item.notes,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted_at=item.deleted_at,
        )

    def update_from_domain(self, item: BucketListItem) -> None:
        self.destination_kind = item.destination_kind.value
        self.destination_name = item.destination_name
        self.normalized_destination_name = item.normalized_destination_name
        self.parent_country = item.parent_country
        self.ideal_days = item.ideal_days
        self.display_order = item.display_order
        self.notes = item.notes
        self.is_active = item.is_active
        self.updated_at = item.updated_at
        self.deleted_at = item.deleted_at

    def to_domain(self) -> BucketListItem:
        return BucketListItem(
            id=UUID(self.id),
            destination_kind=BucketDestinationKindEnum(self.destination_kind),
            destination_name=self.destination_name,
            normalized_destination_name=self.normalized_destination_name,
            parent_country=self.parent_country,
            ideal_days=self.ideal_days,
            display_order=self.display_order,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )


class CustomerPersonalCalendarRow(CustomerBase):
    __tablename__ = "customer_personal_calendars"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, calendar: PersonalCalendar) -> CustomerPersonalCalendarRow:
        return cls(
            id=str(calendar.id),
            account_id=str(calendar.account_id),
            created_at=calendar.created_at,
            updated_at=calendar.updated_at,
        )

    def update_from_domain(self, calendar: PersonalCalendar) -> None:
        self.updated_at = calendar.updated_at

    def to_domain(
        self,
        events: list[PersonalCalendarEventItem],
        periods: list[PersonalCalendarPeriodItem],
    ) -> PersonalCalendar:
        return PersonalCalendar(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            events=events,
            periods=periods,
        )


class CustomerPersonalCalendarEventRow(CustomerBase):
    __tablename__ = "customer_personal_calendar_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('birthday', 'anniversary', 'special_occasion')",
            name="ck_customer_personal_calendar_event_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customer_personal_calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    birthday_for: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anniversary_for: Mapped[str | None] = mapped_column(String(64), nullable=True)
    person_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person1_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person2_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    holiday_types: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(
        cls,
        *,
        calendar_id: UUID,
        item: PersonalCalendarEventItem,
    ) -> CustomerPersonalCalendarEventRow:
        return cls(
            id=str(item.id),
            calendar_id=str(calendar_id),
            event_type=item.event_type.value,
            birthday_for=item.birthday_for.value if item.birthday_for else None,
            anniversary_for=item.anniversary_for.value if item.anniversary_for else None,
            person_name=item.person_name,
            person1_name=item.person1_name,
            person2_name=item.person2_name,
            event_name=item.event_name,
            event_date=item.event_date,
            holiday_types=json.dumps([value.value for value in item.holiday_types]),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def update_from_domain(self, item: PersonalCalendarEventItem) -> None:
        self.event_type = item.event_type.value
        self.birthday_for = item.birthday_for.value if item.birthday_for else None
        self.anniversary_for = item.anniversary_for.value if item.anniversary_for else None
        self.person_name = item.person_name
        self.person1_name = item.person1_name
        self.person2_name = item.person2_name
        self.event_name = item.event_name
        self.event_date = item.event_date
        self.holiday_types = json.dumps([value.value for value in item.holiday_types])
        self.updated_at = item.updated_at

    def to_domain(self) -> PersonalCalendarEventItem:
        holiday_types = [HolidayTypeEnum(value) for value in json.loads(self.holiday_types)]
        return PersonalCalendarEventItem(
            id=UUID(self.id),
            event_type=PersonalCalendarEventTypeEnum(self.event_type),
            event_date=self.event_date,
            holiday_types=holiday_types,
            birthday_for=BirthdayForEnum(self.birthday_for) if self.birthday_for else None,
            anniversary_for=AnniversaryForEnum(self.anniversary_for)
            if self.anniversary_for
            else None,
            person_name=self.person_name,
            person1_name=self.person1_name,
            person2_name=self.person2_name,
            event_name=self.event_name,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class CustomerPersonalCalendarPeriodRow(CustomerBase):
    __tablename__ = "customer_personal_calendar_periods"
    __table_args__ = (
        CheckConstraint(
            "period_end >= period_start",
            name="ck_customer_personal_calendar_period_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customer_personal_calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    is_date_flexible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    holiday_types: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(
        cls,
        *,
        calendar_id: UUID,
        item: PersonalCalendarPeriodItem,
    ) -> CustomerPersonalCalendarPeriodRow:
        return cls(
            id=str(item.id),
            calendar_id=str(calendar_id),
            period_name=item.period_name,
            period_start=item.period_start,
            period_end=item.period_end,
            is_date_flexible=item.is_date_flexible,
            holiday_types=json.dumps([value.value for value in item.holiday_types]),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def update_from_domain(self, item: PersonalCalendarPeriodItem) -> None:
        self.period_name = item.period_name
        self.period_start = item.period_start
        self.period_end = item.period_end
        self.is_date_flexible = item.is_date_flexible
        self.holiday_types = json.dumps([value.value for value in item.holiday_types])
        self.updated_at = item.updated_at

    def to_domain(self) -> PersonalCalendarPeriodItem:
        holiday_types = [HolidayTypeEnum(value) for value in json.loads(self.holiday_types)]
        return PersonalCalendarPeriodItem(
            id=UUID(self.id),
            period_name=self.period_name,
            period_start=self.period_start,
            period_end=self.period_end,
            is_date_flexible=self.is_date_flexible,
            holiday_types=holiday_types,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
