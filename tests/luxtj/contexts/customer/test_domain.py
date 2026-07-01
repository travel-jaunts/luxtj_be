from uuid import uuid7

import pytest

from luxtj.contexts.customer.domain.bucket_list import BucketList
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.contexts.customer.domain.errors import (
    BucketListItemAlreadyExistsError,
    BucketListItemNotFoundError,
    InvalidIdealDaysError,
)


async def test_bucket_list_add_item_and_emit_event(customer_account_id) -> None:
    bucket_list = BucketList.create(account_id=customer_account_id)

    item = bucket_list.add_item(
        destination_kind=BucketDestinationKindEnum.CITY,
        destination_name="Paris",
        parent_country="France",
        ideal_days=4,
        display_order=1,
    )

    assert item.destination_name == "Paris"
    events = bucket_list.pull_events()
    assert len(events) == 1
    assert events[0].type == "com.luxtj.customer.bucket_list.item.created.v1"


async def test_bucket_list_rejects_duplicate_active_destination(customer_account_id) -> None:
    bucket_list = BucketList.create(account_id=customer_account_id)
    bucket_list.add_item(
        destination_kind=BucketDestinationKindEnum.CITY,
        destination_name="Paris",
        parent_country="France",
        ideal_days=4,
    )

    with pytest.raises(BucketListItemAlreadyExistsError):
        bucket_list.add_item(
            destination_kind=BucketDestinationKindEnum.CITY,
            destination_name="  paris  ",
            parent_country="France",
            ideal_days=3,
        )


async def test_bucket_list_update_and_delete_emit_events(customer_account_id) -> None:
    bucket_list = BucketList.create(account_id=customer_account_id)
    item = bucket_list.add_item(
        destination_kind=BucketDestinationKindEnum.PLACE,
        destination_name="Eiffel Tower",
        parent_country="France",
        ideal_days=2,
    )
    bucket_list.pull_events()

    updated = bucket_list.update_item(
        item_id=item.id,
        ideal_days=3,
        display_order=5,
        notes="sunset visit",
    )
    assert updated.ideal_days == 3

    deleted = bucket_list.delete_item(item_id=item.id)
    assert deleted.deleted_at is not None

    events = bucket_list.pull_events()
    assert [event.type for event in events] == [
        "com.luxtj.customer.bucket_list.item.updated.v1",
        "com.luxtj.customer.bucket_list.item.deleted.v1",
    ]


async def test_bucket_list_invariants(customer_account_id) -> None:
    bucket_list = BucketList.create(account_id=customer_account_id)

    with pytest.raises(InvalidIdealDaysError):
        bucket_list.add_item(
            destination_kind=BucketDestinationKindEnum.CITY,
            destination_name="Paris",
            parent_country="France",
            ideal_days=0,
        )

    with pytest.raises(BucketListItemNotFoundError):
        bucket_list.update_item(
            item_id=uuid7(),
            ideal_days=1,
            display_order=None,
            notes=None,
        )
