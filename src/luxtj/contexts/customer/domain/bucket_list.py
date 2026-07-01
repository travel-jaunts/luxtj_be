from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid7

from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.contexts.customer.domain.errors import (
    BucketListItemAlreadyExistsError,
    BucketListItemNotFoundError,
    InvalidIdealDaysError,
)
from luxtj.shared_kernel.domain.events import BaseDomainEvent
from luxtj.utils import timeutils


def _normalize_destination(value: str) -> str:
    return " ".join(value.split()).strip().casefold()


@dataclass
class BucketListItem:
    id: UUID
    destination_kind: BucketDestinationKindEnum
    destination_name: str
    parent_country: str | None
    ideal_days: int
    display_order: int
    notes: str | None
    normalized_destination_name: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None


@dataclass
class BucketList:
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[BucketListItem] = field(default_factory=list)
    _events: list[BaseDomainEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create(cls, *, account_id: UUID) -> BucketList:
        now = timeutils.datetime_now()
        return cls(
            id=uuid7(),
            account_id=account_id,
            created_at=now,
            updated_at=now,
        )

    def active_items(self) -> list[BucketListItem]:
        active = [item for item in self.items if item.is_active]
        return sorted(active, key=lambda item: (item.display_order, item.created_at))

    def add_item(
        self,
        *,
        destination_kind: BucketDestinationKindEnum,
        destination_name: str,
        parent_country: str | None,
        ideal_days: int,
        display_order: int = 0,
        notes: str | None = None,
    ) -> BucketListItem:
        from luxtj.contexts.customer.domain.events import BucketListItemCreated

        if ideal_days <= 0:
            raise InvalidIdealDaysError("ideal_days must be greater than zero")

        normalized_destination_name = _normalize_destination(destination_name)
        if self._has_active_duplicate(
            destination_kind=destination_kind,
            normalized_destination_name=normalized_destination_name,
        ):
            raise BucketListItemAlreadyExistsError(
                f"Destination {destination_name!r} already exists in bucket list"
            )

        now = timeutils.datetime_now()
        item = BucketListItem(
            id=uuid7(),
            destination_kind=destination_kind,
            destination_name=destination_name.strip(),
            parent_country=parent_country.strip() if parent_country else None,
            ideal_days=ideal_days,
            display_order=display_order,
            notes=notes.strip() if notes else None,
            normalized_destination_name=normalized_destination_name,
            created_at=now,
            updated_at=now,
        )
        self.items.append(item)
        self.updated_at = now
        self.record_event(
            BucketListItemCreated.from_item(
                account_id=self.account_id,
                bucket_list_id=self.id,
                item=item,
            )
        )
        return item

    def update_item(
        self,
        *,
        item_id: UUID,
        ideal_days: int | None,
        display_order: int | None,
        notes: str | None,
    ) -> BucketListItem:
        from luxtj.contexts.customer.domain.events import BucketListItemUpdated

        item = self._find_active_item(item_id)
        if ideal_days is not None:
            if ideal_days <= 0:
                raise InvalidIdealDaysError("ideal_days must be greater than zero")
            item.ideal_days = ideal_days
        if display_order is not None:
            item.display_order = display_order
        if notes is not None:
            item.notes = notes.strip() if notes else None
        now = timeutils.datetime_now()
        item.updated_at = now
        self.updated_at = now

        self.record_event(
            BucketListItemUpdated.from_item(
                account_id=self.account_id,
                bucket_list_id=self.id,
                item=item,
            )
        )
        return item

    def delete_item(self, *, item_id: UUID) -> BucketListItem:
        from luxtj.contexts.customer.domain.events import BucketListItemDeleted

        item = self._find_active_item(item_id)
        now = timeutils.datetime_now()
        item.deleted_at = now
        item.updated_at = now
        self.updated_at = now
        self.record_event(
            BucketListItemDeleted.from_item(
                account_id=self.account_id,
                bucket_list_id=self.id,
                item=item,
            )
        )
        return item

    def _find_active_item(self, item_id: UUID) -> BucketListItem:
        for item in self.items:
            if item.id == item_id and item.is_active:
                return item
        raise BucketListItemNotFoundError(f"Bucket list item {item_id} not found")

    def _has_active_duplicate(
        self,
        *,
        destination_kind: BucketDestinationKindEnum,
        normalized_destination_name: str,
    ) -> bool:
        return any(
            item.is_active
            and item.destination_kind == destination_kind
            and item.normalized_destination_name == normalized_destination_name
            for item in self.items
        )

    def record_event(self, event: BaseDomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[BaseDomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
