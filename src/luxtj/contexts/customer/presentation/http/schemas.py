from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from luxtj.contexts.customer.application.bucket_list_recommendation_engine.models import (
    BucketListRecommendationResult,
    FlightDeal,
    FlightSelection,
    HotelDeal,
    HotelSelection,
    PricingBreakdown,
    RecommendationMetadata,
    RecommendationRecommendation,
    UnavailableResult,
    WindowRecommendations,
)
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


class RecommendBucketListDealsBody(ApiSerializerBaseModel):
    origin: str = Field(..., description="Origin airport code or city")
    reference_date: date = Field(..., description="Date used to generate recommendation windows")


class FlightDealSerializer(ApiSerializerBaseModel):
    flight_id: str
    origin: str
    destination: str
    departure_date: date
    price: float
    carrier: str
    flight_number: str
    is_outbound: bool
    is_return: bool
    stops: int
    duration_minutes: int
    cancellation_policy: str
    provider_metadata: dict[str, Any]

    @classmethod
    def from_engine(cls, deal: FlightDeal) -> FlightDealSerializer:
        return cls(
            flight_id=deal.flight_id,
            origin=deal.origin,
            destination=deal.destination,
            departure_date=deal.departure_date,
            price=deal.price,
            carrier=deal.carrier,
            flight_number=deal.flight_number,
            is_outbound=deal.is_outbound,
            is_return=deal.is_return,
            stops=deal.stops,
            duration_minutes=deal.duration_minutes,
            cancellation_policy=deal.cancellation_policy.value,
            provider_metadata=deal.provider_metadata,
        )


class HotelDealSerializer(ApiSerializerBaseModel):
    hotel_id: str
    name: str
    destination: str
    tier: str
    check_in: date
    check_out: date
    price_per_night: float
    total_price: float
    rating: float | None
    reviews_count: int
    cancellation_policy: str
    provider_metadata: dict[str, Any]

    @classmethod
    def from_engine(cls, deal: HotelDeal) -> HotelDealSerializer:
        return cls(
            hotel_id=deal.hotel_id,
            name=deal.name,
            destination=deal.destination,
            tier=deal.tier.value,
            check_in=deal.check_in,
            check_out=deal.check_out,
            price_per_night=deal.price_per_night,
            total_price=deal.total_price,
            rating=deal.rating,
            reviews_count=deal.reviews_count,
            cancellation_policy=deal.cancellation_policy.value,
            provider_metadata=deal.provider_metadata,
        )


class HotelSelectionSerializer(ApiSerializerBaseModel):
    destination_name: str
    requested_days: int
    hotel: HotelDealSerializer

    @classmethod
    def from_engine(cls, selection: HotelSelection) -> HotelSelectionSerializer:
        return cls(
            destination_name=selection.destination.name,
            requested_days=selection.destination.days,
            hotel=HotelDealSerializer.from_engine(selection.hotel_deal),
        )


class FlightSelectionSerializer(ApiSerializerBaseModel):
    outbound: FlightDealSerializer
    return_flight: FlightDealSerializer

    @classmethod
    def from_engine(cls, selection: FlightSelection) -> FlightSelectionSerializer:
        return cls(
            outbound=FlightDealSerializer.from_engine(selection.outbound),
            return_flight=FlightDealSerializer.from_engine(selection.return_flight),
        )


class PricingBreakdownSerializer(ApiSerializerBaseModel):
    flights_cost: float
    hotels_cost: float
    total_cost: float

    @classmethod
    def from_engine(cls, pricing: PricingBreakdown) -> PricingBreakdownSerializer:
        return cls(
            flights_cost=pricing.flights_cost,
            hotels_cost=pricing.hotels_cost,
            total_cost=pricing.total_cost,
        )


class RecommendationMetadataSerializer(ApiSerializerBaseModel):
    generated_at: datetime
    version: str
    departure_date: date

    @classmethod
    def from_engine(cls, metadata: RecommendationMetadata) -> RecommendationMetadataSerializer:
        return cls(
            generated_at=metadata.generated_at,
            version=metadata.version,
            departure_date=metadata.departure_date,
        )


class AvailableRecommendationSerializer(ApiSerializerBaseModel):
    status: Literal["available"] = "available"
    recommendation_id: str
    departure_window: str
    departure_date: date
    return_date: date
    flights: FlightSelectionSerializer
    hotels: list[HotelSelectionSerializer]
    pricing: PricingBreakdownSerializer
    score: float
    score_breakdown: dict[str, float]
    explanation: str
    provider_transparency: dict[str, Any]
    metadata: RecommendationMetadataSerializer

    @classmethod
    def from_engine(
        cls, recommendation: RecommendationRecommendation
    ) -> AvailableRecommendationSerializer:
        return cls(
            recommendation_id=recommendation.recommendation_id,
            departure_window=recommendation.departure_window,
            departure_date=recommendation.departure_date,
            return_date=recommendation.return_date,
            flights=FlightSelectionSerializer.from_engine(recommendation.flights),
            hotels=[HotelSelectionSerializer.from_engine(item) for item in recommendation.hotels],
            pricing=PricingBreakdownSerializer.from_engine(recommendation.pricing),
            score=recommendation.score,
            score_breakdown=recommendation.score_breakdown,
            explanation=recommendation.explanation,
            provider_transparency=recommendation.provider_transparency,
            metadata=RecommendationMetadataSerializer.from_engine(recommendation.metadata),
        )


class UnavailableRecommendationSerializer(ApiSerializerBaseModel):
    status: Literal["unavailable"] = "unavailable"
    tier: str
    reason_codes: list[str]
    explanation: str

    @classmethod
    def from_engine(
        cls, unavailable: UnavailableResult
    ) -> UnavailableRecommendationSerializer:
        return cls(
            tier=unavailable.tier.value,
            reason_codes=unavailable.reason_codes,
            explanation=unavailable.explanation,
        )


RecommendationOptionSerializer = (
    AvailableRecommendationSerializer | UnavailableRecommendationSerializer
)


def _serialize_recommendation_option(
    value: RecommendationRecommendation | UnavailableResult,
) -> RecommendationOptionSerializer:
    if isinstance(value, RecommendationRecommendation):
        return AvailableRecommendationSerializer.from_engine(value)
    return UnavailableRecommendationSerializer.from_engine(value)


class WindowRecommendationsSerializer(ApiSerializerBaseModel):
    window_name: str
    departure_start: date
    departure_end: date
    lite: RecommendationOptionSerializer
    plus: RecommendationOptionSerializer
    ultra: RecommendationOptionSerializer

    @classmethod
    def from_engine(cls, window: WindowRecommendations) -> WindowRecommendationsSerializer:
        return cls(
            window_name=window.window_name,
            departure_start=window.departure_start,
            departure_end=window.departure_end,
            lite=_serialize_recommendation_option(window.lite),
            plus=_serialize_recommendation_option(window.plus),
            ultra=_serialize_recommendation_option(window.ultra),
        )


class BucketListRecommendationResultSerializer(ApiSerializerBaseModel):
    windows: list[WindowRecommendationsSerializer]
    generated_at: datetime

    @classmethod
    def from_engine(
        cls, result: BucketListRecommendationResult
    ) -> BucketListRecommendationResultSerializer:
        return cls(
            windows=[WindowRecommendationsSerializer.from_engine(item) for item in result.windows],
            generated_at=result.generated_at,
        )
