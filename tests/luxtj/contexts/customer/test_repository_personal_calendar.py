from datetime import date
from uuid import uuid7

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    HolidayTypeEnum,
)
from luxtj.contexts.customer.domain.personal_calendar import PersonalCalendar
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import CustomerBase
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPersonalCalendarRepository,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(CustomerBase.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as value:
        yield value

    await engine.dispose()


async def test_personal_calendar_repository_add_get_and_save(session) -> None:
    repository = SqlAlchemyPersonalCalendarRepository(session)
    account_id = uuid7()
    calendar = PersonalCalendar.create(account_id=account_id)
    birthday = calendar.add_birthday_event(
        birthday_for=BirthdayForEnum.SPOUSE_BIRTHDAY,
        person_name="Asha",
        event_date=date(2026, 5, 11),
        holiday_types=[HolidayTypeEnum.HONEYMOONS_AND_ROMANTIC_HOLIDAYS],
    )
    calendar.add_period(
        period_name="Summer Break",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 8),
        is_date_flexible=True,
        holiday_types=[HolidayTypeEnum.ALL_INCLUSIVE_LUXURY_DEALS],
    )

    await repository.add(calendar)
    await session.commit()

    fetched = await repository.get_by_account_id(account_id)
    assert fetched is not None
    assert len(fetched.events) == 1
    assert fetched.events[0].person_name == "Asha"
    assert len(fetched.periods) == 1

    fetched.add_anniversary_event(
        anniversary_for=AnniversaryForEnum.MY_ANNIVERSARY,
        person1_name="Asha",
        person2_name="Rohit",
        event_date=date(2026, 7, 20),
        holiday_types=[HolidayTypeEnum.SIGNATURE_EXPERIENCES],
    )
    await repository.save(fetched)
    await session.commit()

    reloaded = await repository.get_by_account_id(account_id)
    assert reloaded is not None
    assert len(reloaded.events) == 2
    assert any(item.id == birthday.id for item in reloaded.events)
