from datetime import date

import pytest

from luxtj.contexts.customer.application.commands import (
    AddPersonalCalendarEventCommand,
    AddPersonalCalendarPeriodCommand,
)
from luxtj.contexts.customer.application.use_cases import (
    AddPersonalCalendarEvent,
    AddPersonalCalendarPeriod,
    GetPersonalCalendarConsolidatedView,
    GetPersonalCalendarHolidayTypes,
)
from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
from luxtj.contexts.customer.domain.errors import InvalidHolidayTypesError


async def test_add_personal_calendar_event_loads_or_creates(
    personal_calendar_repository, customer_account_id
) -> None:
    use_case = AddPersonalCalendarEvent(repository=personal_calendar_repository)

    item = await use_case(
        AddPersonalCalendarEventCommand(
            account_id=customer_account_id,
            event_type=PersonalCalendarEventTypeEnum.BIRTHDAY,
            birthday_for=BirthdayForEnum.MY_BIRTHDAY,
            person_name="Me",
            event_date=date(2026, 1, 1),
            holiday_types=[HolidayTypeEnum.SIGNATURE_EXPERIENCES],
        )
    )
    assert item.event_type == "birthday"

    second = await use_case(
        AddPersonalCalendarEventCommand(
            account_id=customer_account_id,
            event_type=PersonalCalendarEventTypeEnum.ANNIVERSARY,
            anniversary_for=AnniversaryForEnum.PARENTS,
            person1_name="A",
            person2_name="B",
            event_date=date(2026, 2, 2),
            holiday_types=[HolidayTypeEnum.HONEYMOONS_AND_ROMANTIC_HOLIDAYS],
        )
    )
    assert second.event_type == "anniversary"


async def test_add_personal_calendar_period_validates_holiday_types(
    personal_calendar_repository, customer_account_id
) -> None:
    use_case = AddPersonalCalendarPeriod(repository=personal_calendar_repository)
    with pytest.raises(InvalidHolidayTypesError):
        await use_case(
            AddPersonalCalendarPeriodCommand(
                account_id=customer_account_id,
                period_name="Trip",
                period_start=date(2026, 1, 10),
                period_end=date(2026, 1, 20),
                is_date_flexible=False,
                holiday_types=[
                    HolidayTypeEnum.SIGNATURE_EXPERIENCES,
                    HolidayTypeEnum.DISNEY_AND_EURAIL_TICKETS,
                    HolidayTypeEnum.FAMILY_LUXURY_HOLIDAYS,
                    HolidayTypeEnum.WELLNESS_AND_SPA_RETREATS,
                ],
            )
        )


async def test_get_holiday_types_returns_backend_list() -> None:
    use_case = GetPersonalCalendarHolidayTypes()
    response = await use_case()
    assert "Signature Experiences" in response.holiday_types


async def test_get_personal_calendar_consolidated_view_returns_events_and_periods(
    personal_calendar_repository, customer_account_id
) -> None:
    add_event = AddPersonalCalendarEvent(repository=personal_calendar_repository)
    add_period = AddPersonalCalendarPeriod(repository=personal_calendar_repository)
    get_view = GetPersonalCalendarConsolidatedView(repository=personal_calendar_repository)

    await add_event(
        AddPersonalCalendarEventCommand(
            account_id=customer_account_id,
            event_type=PersonalCalendarEventTypeEnum.BIRTHDAY,
            birthday_for=BirthdayForEnum.MY_BIRTHDAY,
            person_name="Me",
            event_date=date(2026, 1, 2),
            holiday_types=[HolidayTypeEnum.SIGNATURE_EXPERIENCES],
        )
    )
    await add_period(
        AddPersonalCalendarPeriodCommand(
            account_id=customer_account_id,
            period_name="Spring Vacation",
            period_start=date(2026, 3, 10),
            period_end=date(2026, 3, 20),
            is_date_flexible=False,
            holiday_types=[HolidayTypeEnum.FAMILY_LUXURY_HOLIDAYS],
        )
    )

    response = await get_view(customer_account_id)
    assert response.account_id == customer_account_id
    assert len(response.items) == 2
    assert {item.item_type for item in response.items} == {"event", "period"}
