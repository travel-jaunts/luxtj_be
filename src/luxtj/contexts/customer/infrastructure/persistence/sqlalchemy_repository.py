from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.customer.domain.bucket_list import BucketList
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import (
    CustomerBucketListItemRow,
    CustomerBucketListRow,
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
