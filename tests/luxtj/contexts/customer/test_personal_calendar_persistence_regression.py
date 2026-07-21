from datetime import date
from uuid import uuid7

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from luxtj.contexts.customer.application.commands import (
    AddPersonalCalendarEventCommand,
    AddPersonalCalendarPeriodCommand,
)
from luxtj.contexts.customer.application.use_cases import (
    AddPersonalCalendarEvent,
    AddPersonalCalendarPeriod,
)
from luxtj.contexts.customer.domain.enums import (
    BirthdayForEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import (
    CustomerBase,
    CustomerPersonalCalendarEventRow,
    CustomerPersonalCalendarPeriodRow,
    CustomerPersonalCalendarRow,
)
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPersonalCalendarRepository,
)
from luxtj.shared_kernel.infrastructure.persistence.sqlalchemy import session_scope


@pytest.fixture
async def production_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(CustomerBase.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_personal_calendar_write_flow_persists_once_with_production_session_settings(
    production_session_factory,
) -> None:
    account_id = uuid7()

    async with session_scope(production_session_factory) as session:
        repository = SqlAlchemyPersonalCalendarRepository(session)
        add_event = AddPersonalCalendarEvent(repository=repository)
        await add_event(
            AddPersonalCalendarEventCommand(
                account_id=account_id,
                event_type=PersonalCalendarEventTypeEnum.BIRTHDAY,
                event_date=date(2026, 8, 10),
                holiday_types=[HolidayTypeEnum.WELLNESS_AND_SPA_RETREATS],
                birthday_for=BirthdayForEnum.MY_BIRTHDAY,
                person_name="Alex",
            )
        )

    async with session_scope(production_session_factory) as session:
        repository = SqlAlchemyPersonalCalendarRepository(session)
        calendar = await repository.get_by_account_id(account_id)
        assert calendar is not None
        assert len(calendar.events) == 1
        assert calendar.events[0].person_name == "Alex"

        add_period = AddPersonalCalendarPeriod(repository=repository)
        await add_period(
            AddPersonalCalendarPeriodCommand(
                account_id=account_id,
                period_name="Summer Break",
                period_start=date(2026, 8, 20),
                period_end=date(2026, 8, 27),
                is_date_flexible=False,
                holiday_types=[HolidayTypeEnum.FAMILY_LUXURY_HOLIDAYS],
            )
        )

    async with session_scope(production_session_factory) as session:
        repository = SqlAlchemyPersonalCalendarRepository(session)
        calendar = await repository.get_by_account_id(account_id)
        assert calendar is not None
        assert len(calendar.events) == 1
        assert len(calendar.periods) == 1

        calendar_count = await session.scalar(
            select(func.count())
            .select_from(CustomerPersonalCalendarRow)
            .where(CustomerPersonalCalendarRow.account_id == str(account_id))
        )
        event_count = await session.scalar(
            select(func.count())
            .select_from(CustomerPersonalCalendarEventRow)
            .where(CustomerPersonalCalendarEventRow.calendar_id == str(calendar.id))
        )
        period_count = await session.scalar(
            select(func.count())
            .select_from(CustomerPersonalCalendarPeriodRow)
            .where(CustomerPersonalCalendarPeriodRow.calendar_id == str(calendar.id))
        )

        assert calendar_count == 1
        assert event_count == 1
        assert period_count == 1
