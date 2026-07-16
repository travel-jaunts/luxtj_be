from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid7

from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
from luxtj.contexts.customer.domain.errors import (
    InvalidPeriodDateRangeError,
    InvalidPersonalCalendarEventError,
)
from luxtj.contexts.customer.domain.holiday_types import normalize_holiday_types
from luxtj.utils import timeutils


def _clean_text(value: str, *, field_name: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        raise InvalidPersonalCalendarEventError(f"{field_name} is required")
    return cleaned


@dataclass
class PersonalCalendarEventItem:
    id: UUID
    event_type: PersonalCalendarEventTypeEnum
    event_date: date
    holiday_types: list[HolidayTypeEnum]
    birthday_for: BirthdayForEnum | None
    anniversary_for: AnniversaryForEnum | None
    person_name: str | None
    person1_name: str | None
    person2_name: str | None
    event_name: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class PersonalCalendarPeriodItem:
    id: UUID
    period_name: str
    period_start: date
    period_end: date
    is_date_flexible: bool
    holiday_types: list[HolidayTypeEnum]
    created_at: datetime
    updated_at: datetime


@dataclass
class PersonalCalendar:
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime
    events: list[PersonalCalendarEventItem] = field(default_factory=list)
    periods: list[PersonalCalendarPeriodItem] = field(default_factory=list)

    @classmethod
    def create(cls, *, account_id: UUID) -> PersonalCalendar:
        now = timeutils.datetime_now()
        return cls(
            id=uuid7(),
            account_id=account_id,
            created_at=now,
            updated_at=now,
        )

    def add_birthday_event(
        self,
        *,
        birthday_for: BirthdayForEnum,
        person_name: str,
        event_date: date,
        holiday_types: list[HolidayTypeEnum],
    ) -> PersonalCalendarEventItem:
        now = timeutils.datetime_now()
        item = PersonalCalendarEventItem(
            id=uuid7(),
            event_type=PersonalCalendarEventTypeEnum.BIRTHDAY,
            birthday_for=birthday_for,
            anniversary_for=None,
            person_name=_clean_text(person_name, field_name="person_name"),
            person1_name=None,
            person2_name=None,
            event_name=None,
            event_date=event_date,
            holiday_types=normalize_holiday_types(holiday_types),
            created_at=now,
            updated_at=now,
        )
        self.events.append(item)
        self.updated_at = now
        return item

    def add_anniversary_event(
        self,
        *,
        anniversary_for: AnniversaryForEnum,
        person1_name: str,
        person2_name: str,
        event_date: date,
        holiday_types: list[HolidayTypeEnum],
    ) -> PersonalCalendarEventItem:
        now = timeutils.datetime_now()
        item = PersonalCalendarEventItem(
            id=uuid7(),
            event_type=PersonalCalendarEventTypeEnum.ANNIVERSARY,
            birthday_for=None,
            anniversary_for=anniversary_for,
            person_name=None,
            person1_name=_clean_text(person1_name, field_name="person1_name"),
            person2_name=_clean_text(person2_name, field_name="person2_name"),
            event_name=None,
            event_date=event_date,
            holiday_types=normalize_holiday_types(holiday_types),
            created_at=now,
            updated_at=now,
        )
        self.events.append(item)
        self.updated_at = now
        return item

    def add_special_occasion_event(
        self,
        *,
        event_name: str,
        event_date: date,
        holiday_types: list[HolidayTypeEnum],
    ) -> PersonalCalendarEventItem:
        now = timeutils.datetime_now()
        item = PersonalCalendarEventItem(
            id=uuid7(),
            event_type=PersonalCalendarEventTypeEnum.SPECIAL_OCCASION,
            birthday_for=None,
            anniversary_for=None,
            person_name=None,
            person1_name=None,
            person2_name=None,
            event_name=_clean_text(event_name, field_name="event_name"),
            event_date=event_date,
            holiday_types=normalize_holiday_types(holiday_types),
            created_at=now,
            updated_at=now,
        )
        self.events.append(item)
        self.updated_at = now
        return item

    def add_period(
        self,
        *,
        period_name: str,
        period_start: date,
        period_end: date,
        is_date_flexible: bool,
        holiday_types: list[HolidayTypeEnum],
    ) -> PersonalCalendarPeriodItem:
        if period_end < period_start:
            raise InvalidPeriodDateRangeError("period_end must be on or after period_start")
        now = timeutils.datetime_now()
        item = PersonalCalendarPeriodItem(
            id=uuid7(),
            period_name=_clean_text(period_name, field_name="period_name"),
            period_start=period_start,
            period_end=period_end,
            is_date_flexible=is_date_flexible,
            holiday_types=normalize_holiday_types(holiday_types),
            created_at=now,
            updated_at=now,
        )
        self.periods.append(item)
        self.updated_at = now
        return item
