from dataclasses import dataclass
from uuid import UUID

from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum


@dataclass(frozen=True)
class AddBucketListItemCommand:
    account_id: UUID
    destination_kind: BucketDestinationKindEnum
    destination_name: str
    parent_country: str | None
    ideal_days: int
    display_order: int = 0
    notes: str | None = None


@dataclass(frozen=True)
class UpdateBucketListItemCommand:
    account_id: UUID
    item_id: UUID
    ideal_days: int | None = None
    display_order: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class DeleteBucketListItemCommand:
    account_id: UUID
    item_id: UUID


@dataclass(frozen=True)
class SuggestDestinationsCommand:
    query: str
    selected_kind: BucketDestinationKindEnum
    selected_name: str | None = None
