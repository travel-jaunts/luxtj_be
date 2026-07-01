from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from luxtj.contexts.customer.application.commands import (
    AddBucketListItemCommand,
    DeleteBucketListItemCommand,
    SuggestDestinationsCommand,
    UpdateBucketListItemCommand,
)
from luxtj.contexts.customer.application.ports import (
    BucketListRepository,
    DestinationSuggestion,
    DestinationSuggestionProvider,
)
from luxtj.contexts.customer.application.queries import GetBucketListQuery
from luxtj.contexts.customer.domain.bucket_list import BucketList, BucketListItem
from luxtj.contexts.customer.domain.events import DestinationSuggestionResolved
from luxtj.shared_kernel.application.event_bus import DomainEventPublisher


@dataclass(frozen=True)
class BucketListItemDTO:
    id: UUID
    destination_kind: str
    destination_name: str
    parent_country: str | None
    ideal_days: int
    display_order: int
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_domain(cls, item: BucketListItem) -> BucketListItemDTO:
        return cls(
            id=item.id,
            destination_kind=item.destination_kind.value,
            destination_name=item.destination_name,
            parent_country=item.parent_country,
            ideal_days=item.ideal_days,
            display_order=item.display_order,
            notes=item.notes,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted_at=item.deleted_at,
        )


@dataclass(frozen=True)
class BucketListDTO:
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[BucketListItemDTO]

    @classmethod
    def from_domain(cls, bucket_list: BucketList, *, include_deleted: bool) -> BucketListDTO:
        if include_deleted:
            items = sorted(
                bucket_list.items, key=lambda value: (value.display_order, value.created_at)
            )
        else:
            items = bucket_list.active_items()
        return cls(
            id=bucket_list.id,
            account_id=bucket_list.account_id,
            created_at=bucket_list.created_at,
            updated_at=bucket_list.updated_at,
            items=[BucketListItemDTO.from_domain(item) for item in items],
        )


@dataclass(frozen=True)
class DestinationSuggestionDTO:
    destination_kind: str
    destination_name: str
    parent_country: str | None
    ideal_days: int

    @classmethod
    def from_port(cls, suggestion: DestinationSuggestion) -> DestinationSuggestionDTO:
        return cls(
            destination_kind=suggestion.destination_kind.value,
            destination_name=suggestion.destination_name,
            parent_country=suggestion.parent_country,
            ideal_days=suggestion.ideal_days,
        )


@dataclass(frozen=True)
class DestinationSuggestionResultDTO:
    selected: DestinationSuggestionDTO
    alternatives: list[DestinationSuggestionDTO]


class AddBucketListItem:
    def __init__(
        self,
        repository: BucketListRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    async def __call__(self, command: AddBucketListItemCommand) -> BucketListItemDTO:
        bucket_list = await self._load_or_create(command.account_id)
        item = bucket_list.add_item(
            destination_kind=command.destination_kind,
            destination_name=command.destination_name,
            parent_country=command.parent_country,
            ideal_days=command.ideal_days,
            display_order=command.display_order,
            notes=command.notes,
        )
        await self._repository.save(bucket_list)
        await self._flush_events(bucket_list)
        return BucketListItemDTO.from_domain(item)

    async def _load_or_create(self, account_id: UUID) -> BucketList:
        bucket_list = await self._repository.get_by_account_id(account_id)
        if bucket_list is None:
            bucket_list = BucketList.create(account_id=account_id)
            await self._repository.add(bucket_list)
        return bucket_list

    async def _flush_events(self, bucket_list: BucketList) -> None:
        for event in bucket_list.pull_events():
            await self._event_publisher.publish(event)


class UpdateBucketListItem:
    def __init__(
        self,
        repository: BucketListRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    async def __call__(self, command: UpdateBucketListItemCommand) -> BucketListItemDTO:
        bucket_list = await self._must_get(command.account_id)
        item = bucket_list.update_item(
            item_id=command.item_id,
            ideal_days=command.ideal_days,
            display_order=command.display_order,
            notes=command.notes,
        )
        await self._repository.save(bucket_list)
        await self._flush_events(bucket_list)
        return BucketListItemDTO.from_domain(item)

    async def _must_get(self, account_id: UUID) -> BucketList:
        bucket_list = await self._repository.get_by_account_id(account_id)
        if bucket_list is None:
            raise KeyError(str(account_id))
        return bucket_list

    async def _flush_events(self, bucket_list: BucketList) -> None:
        for event in bucket_list.pull_events():
            await self._event_publisher.publish(event)


class DeleteBucketListItem:
    def __init__(
        self,
        repository: BucketListRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    async def __call__(self, command: DeleteBucketListItemCommand) -> BucketListItemDTO:
        bucket_list = await self._must_get(command.account_id)
        item = bucket_list.delete_item(item_id=command.item_id)
        await self._repository.save(bucket_list)
        await self._flush_events(bucket_list)
        return BucketListItemDTO.from_domain(item)

    async def _must_get(self, account_id: UUID) -> BucketList:
        bucket_list = await self._repository.get_by_account_id(account_id)
        if bucket_list is None:
            raise KeyError(str(account_id))
        return bucket_list

    async def _flush_events(self, bucket_list: BucketList) -> None:
        for event in bucket_list.pull_events():
            await self._event_publisher.publish(event)


class GetBucketList:
    def __init__(self, repository: BucketListRepository) -> None:
        self._repository = repository

    async def __call__(self, query: GetBucketListQuery) -> BucketListDTO:
        bucket_list = await self._repository.get_by_account_id(query.account_id)
        if bucket_list is None:
            bucket_list = BucketList.create(account_id=query.account_id)
        return BucketListDTO.from_domain(bucket_list, include_deleted=query.include_deleted)


class SuggestDestinations:
    def __init__(
        self,
        provider: DestinationSuggestionProvider,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._provider = provider
        self._event_publisher = event_publisher

    async def __call__(self, command: SuggestDestinationsCommand) -> DestinationSuggestionResultDTO:
        suggestions = await self._provider.suggest(
            query=command.query,
            selected_kind=command.selected_kind,
            selected_name=command.selected_name,
        )
        await self._event_publisher.publish(
            DestinationSuggestionResolved.from_resolution(
                selected_kind=command.selected_kind,
                query=command.query,
                selected_name=command.selected_name,
                alternative_count=len(suggestions.alternatives),
            )
        )
        return DestinationSuggestionResultDTO(
            selected=DestinationSuggestionDTO.from_port(suggestions.selected),
            alternatives=[
                DestinationSuggestionDTO.from_port(item) for item in suggestions.alternatives
            ],
        )
