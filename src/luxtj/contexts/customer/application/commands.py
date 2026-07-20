from dataclasses import dataclass
from datetime import date
from uuid import UUID

from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    BucketDestinationKindEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)


@dataclass(frozen=True)
class AddBucketListItemCommand:
    account_id: UUID
    destination_kind: BucketDestinationKindEnum
    destination_name: str
    parent_country: str | None
    ideal_days: int
    display_order: int = 0
    notes: str | None = None


@dataclass(frozen=True)
class UpdateBucketListItemCommand:
    account_id: UUID
    item_id: UUID
    ideal_days: int | None = None
    display_order: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class DeleteBucketListItemCommand:
    account_id: UUID
    item_id: UUID


@dataclass(frozen=True)
class SuggestDestinationsCommand:
    account_id: UUID
    query: str
    selected_kind: BucketDestinationKindEnum
    selected_name: str | None = None


@dataclass(frozen=True)
class AddPersonalCalendarEventCommand:
    account_id: UUID
    event_type: PersonalCalendarEventTypeEnum
    event_date: date
    holiday_types: list[HolidayTypeEnum]
    birthday_for: BirthdayForEnum | None = None
    anniversary_for: AnniversaryForEnum | None = None
    person_name: str | None = None
    person1_name: str | None = None
    person2_name: str | None = None
    event_name: str | None = None


@dataclass(frozen=True)
class AddPersonalCalendarPeriodCommand:
    account_id: UUID
    period_name: str
    period_start: date
    period_end: date
    is_date_flexible: bool
    holiday_types: list[HolidayTypeEnum]
