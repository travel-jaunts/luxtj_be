from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from luxtj.contexts.customer.application.use_cases import (
    BucketListDTO,
    BucketListItemDTO,
    DestinationSuggestionDTO,
    DestinationSuggestionResultDTO,
    HolidayTypeListDTO,
    PersonalCalendarConsolidatedItemDTO,
    PersonalCalendarConsolidatedViewDTO,
    PersonalCalendarEventItemDTO,
    PersonalCalendarPeriodItemDTO,
)
from luxtj.contexts.customer.domain.enums import (
    AnniversaryForEnum,
    BirthdayForEnum,
    BucketDestinationKindEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
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


class AddPersonalCalendarEventBody(ApiSerializerBaseModel):
    event_type: PersonalCalendarEventTypeEnum
    event_date: date
    holiday_types: list[HolidayTypeEnum]
    birthday_for: BirthdayForEnum | None = None
    anniversary_for: AnniversaryForEnum | None = None
    person_name: str | None = None
    person1_name: str | None = None
    person2_name: str | None = None
    event_name: str | None = None


class AddPersonalCalendarPeriodBody(ApiSerializerBaseModel):
    period_name: str
    period_start: date
    period_end: date
    is_date_flexible: bool
    holiday_types: list[HolidayTypeEnum]


class PersonalCalendarEventItemSerializer(ApiSerializerBaseModel):
    id: UUID
    event_type: str
    event_date: date
    holiday_types: list[str]
    birthday_for: str | None
    anniversary_for: str | None
    person_name: str | None
    person1_name: str | None
    person2_name: str | None
    event_name: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, dto: PersonalCalendarEventItemDTO) -> PersonalCalendarEventItemSerializer:
        return cls(
            id=dto.id,
            event_type=dto.event_type,
            event_date=dto.event_date,
            holiday_types=dto.holiday_types,
            birthday_for=dto.birthday_for,
            anniversary_for=dto.anniversary_for,
            person_name=dto.person_name,
            person1_name=dto.person1_name,
            person2_name=dto.person2_name,
            event_name=dto.event_name,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class PersonalCalendarPeriodItemSerializer(ApiSerializerBaseModel):
    id: UUID
    period_name: str
    period_start: date
    period_end: date
    is_date_flexible: bool
    holiday_types: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, dto: PersonalCalendarPeriodItemDTO) -> PersonalCalendarPeriodItemSerializer:
        return cls(
            id=dto.id,
            period_name=dto.period_name,
            period_start=dto.period_start,
            period_end=dto.period_end,
            is_date_flexible=dto.is_date_flexible,
            holiday_types=dto.holiday_types,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class HolidayTypeListSerializer(ApiSerializerBaseModel):
    holiday_types: list[str]

    @classmethod
    def from_dto(cls, dto: HolidayTypeListDTO) -> HolidayTypeListSerializer:
        return cls(holiday_types=dto.holiday_types)


class PersonalCalendarConsolidatedItemSerializer(ApiSerializerBaseModel):
    item_type: str
    start_date: date
    end_date: date | None
    event_type: str | None
    event_name: str | None
    period_name: str | None
    holiday_types: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(
        cls, dto: PersonalCalendarConsolidatedItemDTO
    ) -> PersonalCalendarConsolidatedItemSerializer:
        return cls(
            item_type=dto.item_type,
            start_date=dto.start_date,
            end_date=dto.end_date,
            event_type=dto.event_type,
            event_name=dto.event_name,
            period_name=dto.period_name,
            holiday_types=dto.holiday_types,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class PersonalCalendarConsolidatedViewSerializer(ApiSerializerBaseModel):
    account_id: UUID
    items: list[PersonalCalendarConsolidatedItemSerializer]

    @classmethod
    def from_dto(
        cls, dto: PersonalCalendarConsolidatedViewDTO
    ) -> PersonalCalendarConsolidatedViewSerializer:
        return cls(
            account_id=dto.account_id,
            items=[PersonalCalendarConsolidatedItemSerializer.from_dto(item) for item in dto.items],
        )
