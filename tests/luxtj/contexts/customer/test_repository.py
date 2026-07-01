from uuid import uuid7

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from luxtj.contexts.customer.domain.bucket_list import BucketList
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_models import CustomerBase
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyBucketListRepository,
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


async def test_repository_add_get_and_save(session) -> None:
    repository = SqlAlchemyBucketListRepository(session)
    account_id = uuid7()
    bucket_list = BucketList.create(account_id=account_id)
    item = bucket_list.add_item(
        destination_kind=BucketDestinationKindEnum.CITY,
        destination_name="Paris",
        parent_country="France",
        ideal_days=4,
    )

    await repository.add(bucket_list)
    await session.commit()

    fetched = await repository.get_by_account_id(account_id)
    assert fetched is not None
    assert fetched.id == bucket_list.id
    assert len(fetched.active_items()) == 1

    fetched.update_item(item_id=item.id, ideal_days=5, display_order=2, notes="updated")
    await repository.save(fetched)
    await session.commit()

    reloaded = await repository.get_by_account_id(account_id)
    assert reloaded is not None
    assert reloaded.active_items()[0].ideal_days == 5


async def test_repository_soft_delete_filters_active(session) -> None:
    repository = SqlAlchemyBucketListRepository(session)
    account_id = uuid7()
    bucket_list = BucketList.create(account_id=account_id)
    item = bucket_list.add_item(
        destination_kind=BucketDestinationKindEnum.PLACE,
        destination_name="Louvre Museum",
        parent_country="France",
        ideal_days=1,
    )
    await repository.add(bucket_list)
    await session.commit()

    current = await repository.get_by_account_id(account_id)
    assert current is not None
    current.delete_item(item_id=item.id)
    await repository.save(current)
    await session.commit()

    reloaded = await repository.get_by_account_id(account_id)
    assert reloaded is not None
    assert reloaded.active_items() == []
    assert len(reloaded.items) == 1
    assert reloaded.items[0].deleted_at is not None
