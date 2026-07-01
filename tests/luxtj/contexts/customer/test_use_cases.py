from luxtj.contexts.customer.application.commands import (
    AddBucketListItemCommand,
    DeleteBucketListItemCommand,
    SuggestDestinationsCommand,
    UpdateBucketListItemCommand,
)
from luxtj.contexts.customer.application.queries import GetBucketListQuery
from luxtj.contexts.customer.application.use_cases import (
    AddBucketListItem,
    DeleteBucketListItem,
    GetBucketList,
    SuggestDestinations,
    UpdateBucketListItem,
)
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum


async def test_add_update_delete_flow_publishes_events(
    bucket_list_repository,
    customer_account_id,
    event_publisher,
) -> None:
    add_use_case = AddBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )
    update_use_case = UpdateBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )
    delete_use_case = DeleteBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )

    added = await add_use_case(
        AddBucketListItemCommand(
            account_id=customer_account_id,
            destination_kind=BucketDestinationKindEnum.CITY,
            destination_name="Paris",
            parent_country="France",
            ideal_days=4,
        )
    )
    assert added.destination_name == "Paris"

    updated = await update_use_case(
        UpdateBucketListItemCommand(
            account_id=customer_account_id,
            item_id=added.id,
            ideal_days=5,
            notes="extended stay",
        )
    )
    assert updated.ideal_days == 5

    deleted = await delete_use_case(
        DeleteBucketListItemCommand(
            account_id=customer_account_id,
            item_id=added.id,
        )
    )
    assert deleted.deleted_at is not None

    types = [event.type for event in event_publisher.events]
    assert "com.luxtj.customer.bucket_list.item.created.v1" in types
    assert "com.luxtj.customer.bucket_list.item.updated.v1" in types
    assert "com.luxtj.customer.bucket_list.item.deleted.v1" in types


async def test_suggest_destinations_uses_provider_and_emits_event(
    suggestion_provider,
    customer_account_id,
    event_publisher,
) -> None:
    use_case = SuggestDestinations(provider=suggestion_provider, event_publisher=event_publisher)

    result = await use_case(
        SuggestDestinationsCommand(
            account_id=customer_account_id,
            query="France",
            selected_kind=BucketDestinationKindEnum.COUNTRY,
            selected_name="France",
        )
    )

    assert result.selected.destination_name == "Paris"
    assert len(result.alternatives) == 2
    assert event_publisher.events[-1].type == "com.luxtj.customer.bucket_list.suggestion.resolved.v1"


async def test_get_bucket_list_returns_only_active_items(
    bucket_list_repository,
    customer_account_id,
    event_publisher,
) -> None:
    add_use_case = AddBucketListItem(repository=bucket_list_repository, event_publisher=event_publisher)
    delete_use_case = DeleteBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )
    get_use_case = GetBucketList(repository=bucket_list_repository)

    item = await add_use_case(
        AddBucketListItemCommand(
            account_id=customer_account_id,
            destination_kind=BucketDestinationKindEnum.PLACE,
            destination_name="Eiffel Tower",
            parent_country="France",
            ideal_days=2,
        )
    )
    await delete_use_case(
        DeleteBucketListItemCommand(account_id=customer_account_id, item_id=item.id)
    )

    active = await get_use_case(GetBucketListQuery(account_id=customer_account_id))
    assert active.items == []

    full = await get_use_case(GetBucketListQuery(account_id=customer_account_id, include_deleted=True))
    assert len(full.items) == 1
