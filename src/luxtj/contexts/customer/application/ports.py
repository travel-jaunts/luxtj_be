from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from luxtj.contexts.customer.domain.bucket_list import BucketList
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum


class BucketListRepository(Protocol):
    async def get_by_account_id(self, account_id: UUID) -> BucketList | None: ...
    async def add(self, bucket_list: BucketList) -> None: ...
    async def save(self, bucket_list: BucketList) -> None: ...


@dataclass(frozen=True)
class DestinationSuggestion:
    destination_kind: BucketDestinationKindEnum
    destination_name: str
    parent_country: str | None
    ideal_days: int


@dataclass(frozen=True)
class DestinationSuggestionResult:
    selected: DestinationSuggestion
    alternatives: list[DestinationSuggestion]


class DestinationSuggestionProvider(Protocol):
    async def suggest(
        self,
        *,
        query: str,
        selected_kind: BucketDestinationKindEnum,
        selected_name: str | None,
    ) -> DestinationSuggestionResult: ...
