from datetime import date

import pytest

from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
from luxtj.contexts.customer.domain.errors import (
    InvalidHolidayTypesError,
    InvalidPeriodDateRangeError,
    InvalidPersonalCalendarEventError,
)
from luxtj.contexts.customer.domain.personal_calendar import PersonalCalendar


async def test_add_birthday_anniversary_special_and_period(customer_account_id) -> None:
    calendar = PersonalCalendar.create(account_id=customer_account_id)

    birthday = calendar.add_birthday_event(
        birthday_for=BirthdayForEnum.MY_BIRTHDAY,
        person_name="Me",
        event_date=date(2026, 11, 2),
        holiday_types=[HolidayTypeEnum.SIGNATURE_EXPERIENCES],
    )
    anniversary = calendar.add_anniversary_event(
        anniversary_for=AnniversaryForEnum.PARENTS,
        person1_name="Raj",
        person2_name="Meera",
        event_date=date(2026, 2, 14),
        holiday_types=[HolidayTypeEnum.HONEYMOONS_AND_ROMANTIC_HOLIDAYS],
    )
    occasion = calendar.add_special_occasion_event(
        event_name="Graduation Celebration",
        event_date=date(2026, 7, 1),
        holiday_types=[HolidayTypeEnum.CULTURE_FOOD_AND_SHOPPING_TOURS],
    )
    period = calendar.add_period(
        period_name="Winter Vacation",
        period_start=date(2026, 12, 20),
        period_end=date(2026, 12, 31),
        is_date_flexible=False,
        holiday_types=[HolidayTypeEnum.FAMILY_LUXURY_HOLIDAYS],
    )

    assert birthday.event_type == PersonalCalendarEventTypeEnum.BIRTHDAY
    assert anniversary.event_type == PersonalCalendarEventTypeEnum.ANNIVERSARY
    assert occasion.event_type == PersonalCalendarEventTypeEnum.SPECIAL_OCCASION
    assert period.period_name == "Winter Vacation"
    assert len(calendar.events) == 3
    assert len(calendar.periods) == 1


async def test_personal_calendar_rejects_invalid_payloads(customer_account_id) -> None:
    calendar = PersonalCalendar.create(account_id=customer_account_id)

    with pytest.raises(InvalidPersonalCalendarEventError):
        calendar.add_special_occasion_event(
            event_name="   ",
            event_date=date(2026, 1, 1),
            holiday_types=[HolidayTypeEnum.SIGNATURE_EXPERIENCES],
        )

    with pytest.raises(InvalidHolidayTypesError):
        calendar.add_birthday_event(
            birthday_for=BirthdayForEnum.CHILD_BIRTHDAY,
            person_name="Kid",
            event_date=date(2026, 9, 9),
            holiday_types=[
                HolidayTypeEnum.SIGNATURE_EXPERIENCES,
                HolidayTypeEnum.DISNEY_AND_EURAIL_TICKETS,
                HolidayTypeEnum.FAMILY_LUXURY_HOLIDAYS,
                HolidayTypeEnum.WELLNESS_AND_SPA_RETREATS,
            ],
        )

    with pytest.raises(InvalidPeriodDateRangeError):
        calendar.add_period(
            period_name="Bad Range",
            period_start=date(2026, 10, 10),
            period_end=date(2026, 10, 1),
            is_date_flexible=True,
            holiday_types=[HolidayTypeEnum.ALL_INCLUSIVE_LUXURY_DEALS],
        )
