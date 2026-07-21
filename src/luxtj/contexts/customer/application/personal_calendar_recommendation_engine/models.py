from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from types import MappingProxyType

from luxtj.contexts.customer.domain.enums import HolidayTypeEnum
from luxtj.contexts.customer.domain.errors import PersonalCalendarRecommendationError
from luxtj.contexts.customer.domain.personal_calendar import (
    PersonalCalendarEventItem,
    PersonalCalendarPeriodItem,
)

from .enums import (
    CalendarSourceType,
    CancellationPolicy,
    CrowdLevel,
    DealTier,
    LogisticsComplexity,
    NewsRisk,
    PhysicalIntensity,
    PlanType,
    RankingMode,
    RecommendationStatus,
    RejectionReason,
    SeasonType,
    TravelAdvisory,
    TravelerType,
    WalkingLevel,
)


def _clean_required(value: str, field_name: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        raise PersonalCalendarRecommendationError(f"{field_name} is required")
    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def _currency(value: str) -> str:
    cleaned = value.strip().upper()
    if len(cleaned) != 3 or not cleaned.isalpha():
        raise PersonalCalendarRecommendationError("currency must be a three-letter ISO-style code")
    return cleaned


def _validate_ratio(value: float | None, field_name: str) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise PersonalCalendarRecommendationError(f"{field_name} must be between 0 and 1")


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class TravelParty:
    adults: int = 1
    children_ages: tuple[int, ...] = ()
    rooms: int = 1
    traveler_type: TravelerType = TravelerType.SOLO
    mobility_constraints: tuple[str, ...] = ()
    wheelchair_required: bool = False
    preferred_travel_pace: str | None = None

    def __post_init__(self) -> None:
        if self.adults < 1:
            raise PersonalCalendarRecommendationError("At least one adult traveller is required")
        if any(age < 0 or age > 17 for age in self.children_ages):
            raise PersonalCalendarRecommendationError(
                "children_ages must contain ages from 0 to 17"
            )
        if self.rooms < 1:
            raise PersonalCalendarRecommendationError("rooms must be positive")
        if self.rooms > self.total_travelers:
            raise PersonalCalendarRecommendationError("rooms cannot exceed total travellers")
        if self.children and self.traveler_type not in {
            TravelerType.FAMILY,
            TravelerType.MULTI_GENERATIONAL,
        }:
            object.__setattr__(self, "traveler_type", TravelerType.FAMILY)
        elif self.total_travelers > 1 and self.traveler_type is TravelerType.SOLO:
            inferred = TravelerType.COUPLE if self.total_travelers == 2 else TravelerType.FRIENDS
            object.__setattr__(self, "traveler_type", inferred)
        object.__setattr__(
            self, "preferred_travel_pace", _clean_optional(self.preferred_travel_pace)
        )

    @property
    def children(self) -> int:
        return len(self.children_ages)

    @property
    def total_travelers(self) -> int:
        return self.adults + self.children

    @property
    def mobility_sensitive(self) -> bool:
        return (
            self.wheelchair_required
            or bool(self.mobility_constraints)
            or self.traveler_type is TravelerType.MULTI_GENERATIONAL
        )


@dataclass(frozen=True, slots=True)
class BudgetProfile:
    currency: str
    target_total: Decimal | None = None
    maximum_total: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency", _currency(self.currency))
        for field_name in ("target_total", "maximum_total"):
            value = getattr(self, field_name)
            if value is not None and value <= Decimal("0"):
                raise PersonalCalendarRecommendationError(f"{field_name} must be positive")
        if (
            self.target_total is not None
            and self.maximum_total is not None
            and self.target_total > self.maximum_total
        ):
            raise PersonalCalendarRecommendationError("target_total cannot exceed maximum_total")


@dataclass(frozen=True, slots=True)
class TravelerHistory:
    wishlist: tuple[str, ...] = ()
    rejected_destinations: tuple[str, ...] = ()
    searched_destinations: tuple[str, ...] = ()
    past_booked_destinations: tuple[str, ...] = ()
    liked_places: tuple[str, ...] = ()
    liked_countries: tuple[str, ...] = ()
    liked_hotel_styles: tuple[str, ...] = ()
    preferred_airlines: tuple[str, ...] = ()
    accommodation_preferences: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationPreferences:
    plan_types: tuple[PlanType, ...]
    tiers: tuple[DealTier, ...]
    interests: tuple[str, ...] = ()
    travel_intent: str | None = None

    def __post_init__(self) -> None:
        if not self.plan_types:
            raise PersonalCalendarRecommendationError("At least one plan type is required")
        if not self.tiers:
            raise PersonalCalendarRecommendationError("At least one tier is required")
        if len(set(self.plan_types)) != len(self.plan_types):
            raise PersonalCalendarRecommendationError("plan_types cannot contain duplicates")
        if len(set(self.tiers)) != len(self.tiers):
            raise PersonalCalendarRecommendationError("tiers cannot contain duplicates")
        object.__setattr__(self, "travel_intent", _clean_optional(self.travel_intent))


@dataclass(frozen=True, slots=True)
class PersonalCalendarRecommendationInput:
    account_id: str
    origin_city: str
    origin_country: str
    reference_date: date
    pricing_currency: str
    events: tuple[PersonalCalendarEventItem, ...]
    periods: tuple[PersonalCalendarPeriodItem, ...]
    preferences: RecommendationPreferences
    travel_party: TravelParty = field(default_factory=TravelParty)
    history: TravelerHistory = field(default_factory=TravelerHistory)
    budget: BudgetProfile | None = None
    passport_country: str | None = None
    residency_country: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", _clean_required(self.account_id, "account_id"))
        object.__setattr__(self, "origin_city", _clean_required(self.origin_city, "origin_city"))
        object.__setattr__(
            self,
            "origin_country",
            _clean_required(self.origin_country, "origin_country"),
        )
        object.__setattr__(self, "pricing_currency", _currency(self.pricing_currency))
        object.__setattr__(self, "passport_country", _clean_optional(self.passport_country))
        object.__setattr__(self, "residency_country", _clean_optional(self.residency_country))
        if not self.events and not self.periods:
            raise PersonalCalendarRecommendationError(
                "At least one calendar event or period is required"
            )
        ids = [item.id for item in (*self.events, *self.periods)]
        if len(ids) != len(set(ids)):
            raise PersonalCalendarRecommendationError("Calendar item IDs must be unique")
        if self.budget is not None and self.budget.currency != self.pricing_currency:
            raise PersonalCalendarRecommendationError("budget currency must match pricing_currency")


@dataclass(frozen=True, slots=True)
class TravelWindow:
    name: str
    start_date: date
    end_date: date
    target_date: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_required(self.name, "window name"))
        if self.end_date <= self.start_date:
            raise PersonalCalendarRecommendationError(
                "Travel window end_date must be after start_date"
            )
        if self.target_date is not None and not self.start_date < self.target_date < self.end_date:
            raise PersonalCalendarRecommendationError(
                "An event target_date must be inside the trip, not on a travel boundary"
            )

    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days


@dataclass(frozen=True, slots=True)
class TravelOpportunity:
    source_item_id: str
    source_type: CalendarSourceType
    source_label: str
    holiday_types: tuple[HolidayTypeEnum, ...]
    target_date: date | None
    allowed_start: date
    allowed_end: date
    is_date_flexible: bool
    requires_family_suitability: bool
    windows: tuple[TravelWindow, ...]


@dataclass(frozen=True, slots=True)
class DealSearchRequest:
    account_id: str
    origin_city: str
    origin_country: str
    reference_date: date
    pricing_currency: str
    source_item_id: str
    source_type: CalendarSourceType
    source_label: str
    holiday_types: tuple[HolidayTypeEnum, ...]
    requires_family_suitability: bool
    window: TravelWindow
    allowed_start: date
    allowed_end: date
    plan_type: PlanType
    tier: DealTier
    interests: tuple[str, ...]
    travel_intent: str | None
    travel_party: TravelParty
    history: TravelerHistory
    budget: BudgetProfile | None
    passport_country: str | None
    residency_country: str | None


@dataclass(frozen=True, slots=True)
class DealCandidate:
    candidate_id: str
    provider_id: str
    plan_type: PlanType
    tier: DealTier
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
    cancellation_policy: CancellationPolicy = CancellationPolicy.UNKNOWN
    tags: tuple[str, ...] = ()
    suited_for: tuple[TravelerType, ...] = ()
    origin_city: str | None = None
    package_components_complete: bool = True
    family_friendly: bool = False
    maximum_travelers: int | None = None
    rooms_included: int | None = None
    market_reference_price: Decimal | None = None
    supplier_reliability: float | None = None
    supplier_complaint_ratio: float | None = None
    refund_frequency: float | None = None
    visa_processing_days: int | None = None
    travel_advisory: TravelAdvisory = TravelAdvisory.UNKNOWN
    news_risk: NewsRisk = NewsRisk.UNKNOWN
    accessibility: bool | None = None
    physical_intensity: PhysicalIntensity = PhysicalIntensity.UNKNOWN
    logistics_complexity: LogisticsComplexity = LogisticsComplexity.UNKNOWN
    walking_level: WalkingLevel = WalkingLevel.UNKNOWN
    layovers: int = 0
    flight_duration_hours: float | None = None
    estimated_travel_hours: float | None = None
    internal_transfer_count: int = 0
    travel_pace: str | None = None
    value_additions: tuple[str, ...] = ()
    review_score: float | None = None
    brand_score: float | None = None
    room_quality_score: float | None = None
    authenticity_score: float | None = None
    private_experience: bool = False
    conversion_rate: float | None = None
    click_through_rate: float | None = None
    number_of_bookings: int | None = None
    repeat_booking_rate: float | None = None
    season_type: SeasonType = SeasonType.UNKNOWN
    crowd_level: CrowdLevel = CrowdLevel.UNKNOWN
    luxury_demand: float | None = None
    dream_score: float | None = None
    social_trend: float | None = None
    novelty: float | None = None
    safety_score: float | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "provider_id",
            "name",
            "destination",
            "country",
            "city",
        ):
            object.__setattr__(
                self,
                field_name,
                _clean_required(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "currency", _currency(self.currency))
        object.__setattr__(self, "origin_city", _clean_optional(self.origin_city))
        object.__setattr__(self, "travel_pace", _clean_optional(self.travel_pace))
        object.__setattr__(self, "details", _freeze_mapping(self.details))
        if self.end_date < self.start_date:
            raise PersonalCalendarRecommendationError(
                "candidate end_date cannot be before start_date"
            )
        if self.total_price <= Decimal("0"):
            raise PersonalCalendarRecommendationError("total_price must be positive")
        if self.market_reference_price is not None and self.market_reference_price <= Decimal("0"):
            raise PersonalCalendarRecommendationError("market_reference_price must be positive")
        if not 0.0 <= self.quality_rating <= 5.0:
            raise PersonalCalendarRecommendationError("quality_rating must be between 0 and 5")
        if self.review_count is not None and self.review_count < 0:
            raise PersonalCalendarRecommendationError("review_count cannot be negative")
        if self.maximum_travelers is not None and self.maximum_travelers < 1:
            raise PersonalCalendarRecommendationError("maximum_travelers must be positive")
        if self.rooms_included is not None and self.rooms_included < 1:
            raise PersonalCalendarRecommendationError("rooms_included must be positive")
        for field_name in (
            "supplier_reliability",
            "supplier_complaint_ratio",
            "refund_frequency",
            "brand_score",
            "room_quality_score",
            "authenticity_score",
            "conversion_rate",
            "click_through_rate",
            "repeat_booking_rate",
            "luxury_demand",
            "dream_score",
            "social_trend",
            "novelty",
            "safety_score",
        ):
            _validate_ratio(getattr(self, field_name), field_name)
        if self.review_score is not None and not 0.0 <= self.review_score <= 5.0:
            raise PersonalCalendarRecommendationError("review_score must be between 0 and 5")
        if self.number_of_bookings is not None and self.number_of_bookings < 0:
            raise PersonalCalendarRecommendationError("number_of_bookings cannot be negative")
        if self.visa_processing_days is not None and self.visa_processing_days < 0:
            raise PersonalCalendarRecommendationError("visa_processing_days cannot be negative")
        if self.layovers < 0 or self.internal_transfer_count < 0:
            raise PersonalCalendarRecommendationError("layovers and transfers cannot be negative")
        for field_name in ("flight_duration_hours", "estimated_travel_hours"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise PersonalCalendarRecommendationError(f"{field_name} cannot be negative")

    @property
    def duration_nights(self) -> int:
        return (self.end_date - self.start_date).days


@dataclass(frozen=True, slots=True)
class FilterDecision:
    accepted: bool
    reason_codes: tuple[RejectionReason, ...]


@dataclass(frozen=True, slots=True)
class CandidatePoolStatistics:
    currency: str
    candidate_count: int
    minimum_price: Decimal
    median_price: Decimal
    maximum_price: Decimal
    median_quality_adjusted_price: Decimal


@dataclass(frozen=True, slots=True)
class FeatureVector:
    names: tuple[str, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.names:
            raise PersonalCalendarRecommendationError("FeatureVector must contain features")
        if len(self.names) != len(self.values):
            raise PersonalCalendarRecommendationError(
                "FeatureVector names and values must have equal length"
            )
        if len(set(self.names)) != len(self.names):
            raise PersonalCalendarRecommendationError("FeatureVector names must be unique")
        if any(not 0.0 <= value <= 1.0 for value in self.values):
            raise PersonalCalendarRecommendationError(
                "FeatureVector values must be between 0 and 1"
            )

    def as_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values, strict=True))

    def value(self, name: str) -> float:
        try:
            index = self.names.index(name)
        except ValueError as exc:
            raise KeyError(name) from exc
        return self.values[index]


@dataclass(frozen=True, slots=True)
class BusinessScoreBreakdown:
    date_match: float
    ease_of_travel: float
    product_quality: float
    emotional_fit: float
    cancellation_flexibility: float
    historical_conversion: float
    value_addition: float
    destination_appeal: float

    def as_dict(self) -> dict[str, float]:
        return {
            "date_match": self.date_match,
            "ease_of_travel": self.ease_of_travel,
            "product_quality": self.product_quality,
            "emotional_fit": self.emotional_fit,
            "cancellation_flexibility": self.cancellation_flexibility,
            "historical_conversion": self.historical_conversion,
            "value_addition": self.value_addition,
            "destination_appeal": self.destination_appeal,
        }


@dataclass(frozen=True, slots=True)
class RankingMetadata:
    mode: RankingMode
    feature_schema_version: str
    ranker_version: str
    model_version: str | None
    heuristic_score: float
    ml_score: float | None
    ml_blend_weight: float


@dataclass(frozen=True, slots=True)
class RankingCandidateObservation:
    candidate_id: str
    provider_id: str
    rank: int
    selected: bool
    features: FeatureVector
    heuristic_score: float
    ml_score: float | None
    final_score: float


@dataclass(frozen=True, slots=True)
class RankingObservation:
    account_id: str
    source_item_id: str
    source_type: CalendarSourceType
    window_start: date
    window_end: date
    plan_type: PlanType
    tier: DealTier
    recorded_at: datetime
    ranker_version: str
    model_version: str | None
    candidates: tuple[RankingCandidateObservation, ...]


@dataclass(frozen=True, slots=True)
class DealRecommendation:
    status: RecommendationStatus
    plan_type: PlanType
    tier: DealTier
    candidate: DealCandidate
    final_score: float
    business_score_breakdown: BusinessScoreBreakdown
    ranking_metadata: RankingMetadata
    why_this_won: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnavailableRecommendation:
    status: RecommendationStatus
    plan_type: PlanType
    tier: DealTier
    reason_codes: tuple[RejectionReason, ...]
    message: str


RecommendationOption = DealRecommendation | UnavailableRecommendation


@dataclass(frozen=True, slots=True)
class WindowRecommendationResult:
    window: TravelWindow
    options: tuple[RecommendationOption, ...]


@dataclass(frozen=True, slots=True)
class OpportunityRecommendationResult:
    source_item_id: str
    source_type: CalendarSourceType
    source_label: str
    target_date: date | None
    holiday_types: tuple[HolidayTypeEnum, ...]
    windows: tuple[WindowRecommendationResult, ...]


@dataclass(frozen=True, slots=True)
class PersonalCalendarRecommendationResult:
    account_id: str
    opportunities: tuple[OpportunityRecommendationResult, ...]
    generated_at: datetime
    engine_version: str
