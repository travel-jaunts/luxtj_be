from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class GetBucketListQuery:
    account_id: UUID
    include_deleted: bool = False


@dataclass(frozen=True)
class RecommendBucketListDealsQuery:
    account_id: UUID
    origin: str
    reference_date: date
