from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.enums import (
    CalendarSourceType,
    DealTier,
    PlanType,
    TravelerType,
)
from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.models import (
    BusinessScoreBreakdown,
    DealCandidate,
    DealRecommendation,
    OpportunityRecommendationResult,
    PersonalCalendarRecommendationResult,
    TravelWindow,
    UnavailableRecommendation,
    WindowRecommendationResult,
)
from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.models import (
    RankingMetadata as PersonalCalendarRankingMetadata,
)
from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.models import (
    RecommendationOption as PersonalCalendarRecommendationOption,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class RecommendPersonalCalendarDealsBody(ApiSerializerBaseModel):
    origin_city: str = Field(..., description="Departure city or airport code")
    origin_country: str = Field(..., description="Departure country")
    reference_date: date = Field(..., description="Date from which opportunities are generated")
    pricing_currency: str = Field("GBP", min_length=3, max_length=3)
    calendar_item_id: UUID | None = None
    calendar_item_type: CalendarSourceType | None = None
    plan_types: list[PlanType] = Field(default_factory=lambda: [PlanType.HOTEL_FLIGHT])
    tiers: list[DealTier] = Field(
        default_factory=lambda: [DealTier.LITE, DealTier.PLUS, DealTier.ULTRA]
    )
    adults: int = Field(1, ge=1)
    children_ages: list[int] = Field(default_factory=list)
    rooms: int = Field(1, ge=1)
    traveler_type: TravelerType = TravelerType.SOLO
    mobility_constraints: list[str] = Field(default_factory=list)
    wheelchair_required: bool = False
    preferred_travel_pace: str | None = None
    target_budget: Decimal | None = Field(default=None, gt=0)
    maximum_budget: Decimal | None = Field(default=None, gt=0)
    passport_country: str | None = None
    residency_country: str | None = None
    interests: list[str] = Field(default_factory=list)
    travel_intent: str | None = None

    @model_validator(mode="after")
    def validate_calendar_selector(self) -> RecommendPersonalCalendarDealsBody:
        if (self.calendar_item_id is None) != (self.calendar_item_type is None):
            raise ValueError("calendarItemId and calendarItemType must be supplied together")
        if self.target_budget is not None and self.maximum_budget is not None:
            if self.target_budget > self.maximum_budget:
                raise ValueError("targetBudget cannot exceed maximumBudget")
        return self


class PersonalCalendarDealCandidateSerializer(ApiSerializerBaseModel):
    candidate_id: str
    provider_id: str
    plan_type: str
    tier: str
    name: str
    destination: str
    country: str
    city: str
    start_date: date
    end_date: date
    currency: str
    total_price: Decimal
    quality_rating: float
    review_count: int | None
    cancellation_policy: str
    tags: list[str]
    suited_for: list[str]
    origin_city: str | None
    package_components_complete: bool
    family_friendly: bool
    maximum_travelers: int | None
    rooms_included: int | None
    market_reference_price: Decimal | None
    supplier_reliability: float | None
    supplier_complaint_ratio: float | None
    refund_frequency: float | None
    visa_processing_days: int | None
    travel_advisory: str
    news_risk: str
    accessibility: bool | None
    physical_intensity: str
    logistics_complexity: str
    walking_level: str
    layovers: int
    flight_duration_hours: float | None
    estimated_travel_hours: float | None
    internal_transfer_count: int
    travel_pace: str | None
    value_additions: list[str]
    season_type: str
    crowd_level: str
    details: dict[str, Any]

    @classmethod
    def from_engine(cls, candidate: DealCandidate) -> PersonalCalendarDealCandidateSerializer:
        return cls(
            candidate_id=candidate.candidate_id,
            provider_id=candidate.provider_id,
            plan_type=candidate.plan_type.value,
            tier=candidate.tier.value,
            name=candidate.name,
            destination=candidate.destination,
            country=candidate.country,
            city=candidate.city,
            start_date=candidate.start_date,
            end_date=candidate.end_date,
            currency=candidate.currency,
            total_price=candidate.total_price,
            quality_rating=candidate.quality_rating,
            review_count=candidate.review_count,
            cancellation_policy=candidate.cancellation_policy.value,
            tags=list(candidate.tags),
            suited_for=[value.value for value in candidate.suited_for],
            origin_city=candidate.origin_city,
            package_components_complete=candidate.package_components_complete,
            family_friendly=candidate.family_friendly,
            maximum_travelers=candidate.maximum_travelers,
            rooms_included=candidate.rooms_included,
            market_reference_price=candidate.market_reference_price,
            supplier_reliability=candidate.supplier_reliability,
            supplier_complaint_ratio=candidate.supplier_complaint_ratio,
            refund_frequency=candidate.refund_frequency,
            visa_processing_days=candidate.visa_processing_days,
            travel_advisory=candidate.travel_advisory.value,
            news_risk=candidate.news_risk.value,
            accessibility=candidate.accessibility,
            physical_intensity=candidate.physical_intensity.value,
            logistics_complexity=candidate.logistics_complexity.value,
            walking_level=candidate.walking_level.value,
            layovers=candidate.layovers,
            flight_duration_hours=candidate.flight_duration_hours,
            estimated_travel_hours=candidate.estimated_travel_hours,
            internal_transfer_count=candidate.internal_transfer_count,
            travel_pace=candidate.travel_pace,
            value_additions=list(candidate.value_additions),
            season_type=candidate.season_type.value,
            crowd_level=candidate.crowd_level.value,
            details=dict(candidate.details),
        )


class PersonalCalendarBusinessScoreSerializer(ApiSerializerBaseModel):
    date_match: float
    ease_of_travel: float
    product_quality: float
    emotional_fit: float
    cancellation_flexibility: float
    historical_conversion: float
    value_addition: float
    destination_appeal: float

    @classmethod
    def from_engine(cls, score: BusinessScoreBreakdown) -> PersonalCalendarBusinessScoreSerializer:
        return cls(
            date_match=score.date_match,
            ease_of_travel=score.ease_of_travel,
            product_quality=score.product_quality,
            emotional_fit=score.emotional_fit,
            cancellation_flexibility=score.cancellation_flexibility,
            historical_conversion=score.historical_conversion,
            value_addition=score.value_addition,
            destination_appeal=score.destination_appeal,
        )


class PersonalCalendarRankingMetadataSerializer(ApiSerializerBaseModel):
    mode: str
    feature_schema_version: str
    ranker_version: str
    model_version: str | None
    heuristic_score: float
    ml_score: float | None
    ml_blend_weight: float

    @classmethod
    def from_engine(
        cls, metadata: PersonalCalendarRankingMetadata
    ) -> PersonalCalendarRankingMetadataSerializer:
        return cls(
            mode=metadata.mode.value,
            feature_schema_version=metadata.feature_schema_version,
            ranker_version=metadata.ranker_version,
            model_version=metadata.model_version,
            heuristic_score=metadata.heuristic_score,
            ml_score=metadata.ml_score,
            ml_blend_weight=metadata.ml_blend_weight,
        )


class AvailablePersonalCalendarRecommendationSerializer(ApiSerializerBaseModel):
    status: Literal["available"] = "available"
    plan_type: str
    tier: str
    candidate: PersonalCalendarDealCandidateSerializer
    final_score: float
    business_score_breakdown: PersonalCalendarBusinessScoreSerializer
    ranking_metadata: PersonalCalendarRankingMetadataSerializer
    why_this_won: list[str]

    @classmethod
    def from_engine(
        cls, recommendation: DealRecommendation
    ) -> AvailablePersonalCalendarRecommendationSerializer:
        return cls(
            plan_type=recommendation.plan_type.value,
            tier=recommendation.tier.value,
            candidate=PersonalCalendarDealCandidateSerializer.from_engine(recommendation.candidate),
            final_score=recommendation.final_score,
            business_score_breakdown=PersonalCalendarBusinessScoreSerializer.from_engine(
                recommendation.business_score_breakdown
            ),
            ranking_metadata=PersonalCalendarRankingMetadataSerializer.from_engine(
                recommendation.ranking_metadata
            ),
            why_this_won=list(recommendation.why_this_won),
        )


class UnavailablePersonalCalendarRecommendationSerializer(ApiSerializerBaseModel):
    status: Literal["unavailable"] = "unavailable"
    plan_type: str
    tier: str
    reason_codes: list[str]
    message: str

    @classmethod
    def from_engine(
        cls, recommendation: UnavailableRecommendation
    ) -> UnavailablePersonalCalendarRecommendationSerializer:
        return cls(
            plan_type=recommendation.plan_type.value,
            tier=recommendation.tier.value,
            reason_codes=[value.value for value in recommendation.reason_codes],
            message=recommendation.message,
        )


PersonalCalendarRecommendationOptionSerializer = (
    AvailablePersonalCalendarRecommendationSerializer
    | UnavailablePersonalCalendarRecommendationSerializer
)


def _serialize_personal_calendar_option(
    option: PersonalCalendarRecommendationOption,
) -> PersonalCalendarRecommendationOptionSerializer:
    if isinstance(option, DealRecommendation):
        return AvailablePersonalCalendarRecommendationSerializer.from_engine(option)
    return UnavailablePersonalCalendarRecommendationSerializer.from_engine(option)


class PersonalCalendarTravelWindowSerializer(ApiSerializerBaseModel):
    name: str
    start_date: date
    end_date: date
    target_date: date | None
    nights: int

    @classmethod
    def from_engine(cls, window: TravelWindow) -> PersonalCalendarTravelWindowSerializer:
        return cls(
            name=window.name,
            start_date=window.start_date,
            end_date=window.end_date,
            target_date=window.target_date,
            nights=window.nights,
        )


class PersonalCalendarWindowRecommendationSerializer(ApiSerializerBaseModel):
    window: PersonalCalendarTravelWindowSerializer
    options: list[PersonalCalendarRecommendationOptionSerializer]

    @classmethod
    def from_engine(
        cls, result: WindowRecommendationResult
    ) -> PersonalCalendarWindowRecommendationSerializer:
        return cls(
            window=PersonalCalendarTravelWindowSerializer.from_engine(result.window),
            options=[_serialize_personal_calendar_option(option) for option in result.options],
        )


class PersonalCalendarOpportunityRecommendationSerializer(ApiSerializerBaseModel):
    source_item_id: UUID
    source_type: str
    source_label: str
    target_date: date | None
    holiday_types: list[str]
    windows: list[PersonalCalendarWindowRecommendationSerializer]

    @classmethod
    def from_engine(
        cls, result: OpportunityRecommendationResult
    ) -> PersonalCalendarOpportunityRecommendationSerializer:
        return cls(
            source_item_id=UUID(result.source_item_id),
            source_type=result.source_type.value,
            source_label=result.source_label,
            target_date=result.target_date,
            holiday_types=[value.value for value in result.holiday_types],
            windows=[
                PersonalCalendarWindowRecommendationSerializer.from_engine(window)
                for window in result.windows
            ],
        )


class PersonalCalendarRecommendationResultSerializer(ApiSerializerBaseModel):
    account_id: UUID
    opportunities: list[PersonalCalendarOpportunityRecommendationSerializer]
    generated_at: datetime
    engine_version: str

    @classmethod
    def from_engine(
        cls, result: PersonalCalendarRecommendationResult
    ) -> PersonalCalendarRecommendationResultSerializer:
        return cls(
            account_id=UUID(result.account_id),
            opportunities=[
                PersonalCalendarOpportunityRecommendationSerializer.from_engine(opportunity)
                for opportunity in result.opportunities
            ],
            generated_at=result.generated_at,
            engine_version=result.engine_version,
        )
