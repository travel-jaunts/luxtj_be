from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetBucketListQuery:
    account_id: UUID
