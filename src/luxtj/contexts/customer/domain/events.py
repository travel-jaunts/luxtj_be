from typing import Any
from uuid import UUID

from pydantic import Field

from luxtj.contexts.customer.domain.bucket_list import BucketListItem
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.shared_kernel.domain.events import BaseDomainEvent


class BucketListItemCreated(BaseDomainEvent):
    source: str = "/luxtj/contexts/customer/domain/bucket_list"
    type: str = "com.luxtj.customer.bucket_list.item.created.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_item(
        cls,
        *,
        account_id: UUID,
        bucket_list_id: UUID,
        item: BucketListItem,
    ) -> BucketListItemCreated:
        return cls(
            subject=str(item.id),
            time=item.created_at,
            data={
                "account_id": str(account_id),
                "bucket_list_id": str(bucket_list_id),
                "item_id": str(item.id),
                "destination_kind": item.destination_kind.value,
                "destination_name": item.destination_name,
                "ideal_days": item.ideal_days,
                "created_at": item.created_at.isoformat(),
            },
        )


class BucketListItemUpdated(BaseDomainEvent):
    source: str = "/luxtj/contexts/customer/domain/bucket_list"
    type: str = "com.luxtj.customer.bucket_list.item.updated.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_item(
        cls,
        *,
        account_id: UUID,
        bucket_list_id: UUID,
        item: BucketListItem,
    ) -> BucketListItemUpdated:
        return cls(
            subject=str(item.id),
            time=item.updated_at,
            data={
                "account_id": str(account_id),
                "bucket_list_id": str(bucket_list_id),
                "item_id": str(item.id),
                "destination_kind": item.destination_kind.value,
                "destination_name": item.destination_name,
                "ideal_days": item.ideal_days,
                "updated_at": item.updated_at.isoformat(),
            },
        )


class BucketListItemDeleted(BaseDomainEvent):
    source: str = "/luxtj/contexts/customer/domain/bucket_list"
    type: str = "com.luxtj.customer.bucket_list.item.deleted.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_item(
        cls,
        *,
        account_id: UUID,
        bucket_list_id: UUID,
        item: BucketListItem,
    ) -> BucketListItemDeleted:
        return cls(
            subject=str(item.id),
            time=item.deleted_at,
            data={
                "account_id": str(account_id),
                "bucket_list_id": str(bucket_list_id),
                "item_id": str(item.id),
                "destination_kind": item.destination_kind.value,
                "destination_name": item.destination_name,
                "ideal_days": item.ideal_days,
                "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
            },
        )


class DestinationSuggestionResolved(BaseDomainEvent):
    source: str = "/luxtj/contexts/customer/domain/bucket_list"
    type: str = "com.luxtj.customer.bucket_list.suggestion.resolved.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_resolution(
        cls,
        *,
        selected_kind: BucketDestinationKindEnum,
        query: str,
        selected_name: str | None,
        alternative_count: int,
    ) -> DestinationSuggestionResolved:
        from luxtj.utils import timeutils

        now = timeutils.datetime_now()
        return cls(
            subject=str(query),
            time=now,
            data={
                "selected_kind": selected_kind.value,
                "query": query,
                "selected_name": selected_name,
                "alternative_count": alternative_count,
                "resolved_at": now.isoformat(),
            },
        )
