from datetime import datetime
from uuid import UUID

from pydantic import Field

from luxtj.contexts.customer.application.use_cases import (
    BucketListDTO,
    BucketListItemDTO,
    DestinationSuggestionDTO,
    DestinationSuggestionResultDTO,
)
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class SuggestDestinationsBody(ApiSerializerBaseModel):
    query: str = Field(..., description="Country/city/place query")
    selected_kind: BucketDestinationKindEnum = Field(
        ..., description="Whether selection is country, city, or place"
    )
    selected_name: str | None = Field(
        default=None,
        description="Selected destination name when available",
    )


class AddBucketListItemBody(ApiSerializerBaseModel):
    destination_kind: BucketDestinationKindEnum
    destination_name: str
    parent_country: str | None = None
    ideal_days: int
    display_order: int = 0
    notes: str | None = None


class UpdateBucketListItemBody(ApiSerializerBaseModel):
    ideal_days: int | None = None
    display_order: int | None = None
    notes: str | None = None


class ViewBucketListBody(ApiSerializerBaseModel):
    include_deleted: bool = False


class DestinationSuggestionSerializer(ApiSerializerBaseModel):
    destination_kind: str
    destination_name: str
    parent_country: str | None
    ideal_days: int

    @classmethod
    def from_dto(cls, dto: DestinationSuggestionDTO) -> DestinationSuggestionSerializer:
        return cls(
            destination_kind=dto.destination_kind,
            destination_name=dto.destination_name,
            parent_country=dto.parent_country,
            ideal_days=dto.ideal_days,
        )


class DestinationSuggestionResultSerializer(ApiSerializerBaseModel):
    selected: DestinationSuggestionSerializer
    alternatives: list[DestinationSuggestionSerializer]

    @classmethod
    def from_dto(
        cls,
        dto: DestinationSuggestionResultDTO,
    ) -> DestinationSuggestionResultSerializer:
        return cls(
            selected=DestinationSuggestionSerializer.from_dto(dto.selected),
            alternatives=[
                DestinationSuggestionSerializer.from_dto(item) for item in dto.alternatives
            ],
        )


class BucketListItemSerializer(ApiSerializerBaseModel):
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
    def from_dto(cls, dto: BucketListItemDTO) -> BucketListItemSerializer:
        return cls(
            id=dto.id,
            destination_kind=dto.destination_kind,
            destination_name=dto.destination_name,
            parent_country=dto.parent_country,
            ideal_days=dto.ideal_days,
            display_order=dto.display_order,
            notes=dto.notes,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )


class BucketListSerializer(ApiSerializerBaseModel):
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[BucketListItemSerializer]

    @classmethod
    def from_dto(cls, dto: BucketListDTO) -> BucketListSerializer:
        return cls(
            id=dto.id,
            account_id=dto.account_id,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            items=[BucketListItemSerializer.from_dto(item) for item in dto.items],
        )
