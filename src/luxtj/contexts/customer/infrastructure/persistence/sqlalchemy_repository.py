from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.customer.domain.bucket_list import BucketList
from luxtj.contexts.customer.domain.personal_calendar import PersonalCalendar
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import (
    CustomerBucketListItemRow,
    CustomerBucketListRow,
    CustomerPersonalCalendarEventRow,
    CustomerPersonalCalendarPeriodRow,
    CustomerPersonalCalendarRow,
)


class SqlAlchemyBucketListRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account_id(self, account_id: UUID) -> BucketList | None:
        row = await self._session.scalar(
            select(CustomerBucketListRow).where(CustomerBucketListRow.account_id == str(account_id))
        )
        if row is None:
            return None

        item_rows = await self._session.scalars(
            select(CustomerBucketListItemRow)
            .where(CustomerBucketListItemRow.bucket_list_id == row.id)
            .order_by(CustomerBucketListItemRow.created_at)
        )
        return row.to_domain([item.to_domain() for item in item_rows])

    async def add(self, bucket_list: BucketList) -> None:
        self._session.add(CustomerBucketListRow.from_domain(bucket_list))
        for item in bucket_list.items:
            self._session.add(
                CustomerBucketListItemRow.from_domain(bucket_list_id=bucket_list.id, item=item)
            )

    async def save(self, bucket_list: BucketList) -> None:
        row = await self._session.scalar(
            select(CustomerBucketListRow).where(CustomerBucketListRow.id == str(bucket_list.id))
        )
        if row is None:
            await self.add(bucket_list)
            return

        row.update_from_domain(bucket_list)

        existing_item_rows = await self._session.scalars(
            select(CustomerBucketListItemRow).where(
                CustomerBucketListItemRow.bucket_list_id == str(bucket_list.id)
            )
        )
        existing_by_id = {item.id: item for item in existing_item_rows}

        for item in bucket_list.items:
            found = existing_by_id.get(str(item.id))
            if found is None:
                self._session.add(
                    CustomerBucketListItemRow.from_domain(bucket_list_id=bucket_list.id, item=item)
                )
            else:
                found.update_from_domain(item)


class SqlAlchemyPersonalCalendarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account_id(self, account_id: UUID) -> PersonalCalendar | None:
        row = await self._session.scalar(
            select(CustomerPersonalCalendarRow).where(
                CustomerPersonalCalendarRow.account_id == str(account_id)
            )
        )
        if row is None:
            return None

        event_rows = await self._session.scalars(
            select(CustomerPersonalCalendarEventRow)
            .where(CustomerPersonalCalendarEventRow.calendar_id == row.id)
            .order_by(CustomerPersonalCalendarEventRow.created_at)
        )
        period_rows = await self._session.scalars(
            select(CustomerPersonalCalendarPeriodRow)
            .where(CustomerPersonalCalendarPeriodRow.calendar_id == row.id)
            .order_by(CustomerPersonalCalendarPeriodRow.created_at)
        )
        return row.to_domain(
            events=[item.to_domain() for item in event_rows],
            periods=[item.to_domain() for item in period_rows],
        )

    async def add(self, calendar: PersonalCalendar) -> None:
        self._session.add(CustomerPersonalCalendarRow.from_domain(calendar))
        for item in calendar.events:
            self._session.add(
                CustomerPersonalCalendarEventRow.from_domain(calendar_id=calendar.id, item=item)
            )
        for item in calendar.periods:
            self._session.add(
                CustomerPersonalCalendarPeriodRow.from_domain(calendar_id=calendar.id, item=item)
            )

    async def save(self, calendar: PersonalCalendar) -> None:
        row = await self._session.scalar(
            select(CustomerPersonalCalendarRow).where(
                CustomerPersonalCalendarRow.id == str(calendar.id)
            )
        )
        if row is None:
            await self.add(calendar)
            return

        row.update_from_domain(calendar)

        existing_event_rows = await self._session.scalars(
            select(CustomerPersonalCalendarEventRow).where(
                CustomerPersonalCalendarEventRow.calendar_id == str(calendar.id)
            )
        )
        existing_event_by_id = {item.id: item for item in existing_event_rows}
        for item in calendar.events:
            found = existing_event_by_id.get(str(item.id))
            if found is None:
                self._session.add(
                    CustomerPersonalCalendarEventRow.from_domain(calendar_id=calendar.id, item=item)
                )
            else:
                found.update_from_domain(item)

        existing_period_rows = await self._session.scalars(
            select(CustomerPersonalCalendarPeriodRow).where(
                CustomerPersonalCalendarPeriodRow.calendar_id == str(calendar.id)
            )
        )
        existing_period_by_id = {item.id: item for item in existing_period_rows}
        for item in calendar.periods:
            found = existing_period_by_id.get(str(item.id))
            if found is None:
                self._session.add(
                    CustomerPersonalCalendarPeriodRow.from_domain(
                        calendar_id=calendar.id, item=item
                    )
                )
            else:
                found.update_from_domain(item)
