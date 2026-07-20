from dataclasses import dataclass, field

from .enums import DealTier, UnknownReviewPolicy
from .exceptions import InvalidEngineInputError


@dataclass(frozen=True, slots=True)
class BusinessScoringWeights:
    date_match: float = 0.15
    ease_of_travel: float = 0.15
    product_quality: float = 0.15
    emotional_fit: float = 0.15
    cancellation_flexibility: float = 0.10
    historical_conversion: float = 0.10
    value_addition: float = 0.10
    destination_appeal: float = 0.10

    def __post_init__(self) -> None:
        values = tuple(self.as_dict().values())
        if any(value < 0.0 for value in values):
            raise InvalidEngineInputError("Business scoring weights cannot be negative")
        if abs(sum(values) - 1.0) > 1e-9:
            raise InvalidEngineInputError("Business scoring weights must sum to 1.0")

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
class EngineConfig:
    business_weights: BusinessScoringWeights = field(default_factory=BusinessScoringWeights)
    flexible_period_buffer_days: int = 3
    standard_period_nights: tuple[int, ...] = (2, 3, 4, 5, 7)
    family_period_nights: tuple[int, ...] = (5, 7, 10)
    duration_tolerance_nights: int = 1
    max_windows_per_opportunity: int = 12
    max_concurrent_searches: int = 8
    leap_day_fallback_day: int = 28
    unknown_review_policy: UnknownReviewPolicy = UnknownReviewPolicy.ALLOW_WITH_PENALTY
    unknown_review_confidence: float = 0.40
    ml_blend_weight: float = 0.35
    max_recommendations_per_option: int = 1
    tier_quality_thresholds: tuple[tuple[DealTier, float], ...] = (
        (DealTier.LITE, 4.0),
        (DealTier.PLUS, 4.5),
        (DealTier.ULTRA, 5.0),
    )
    tier_review_count_thresholds: tuple[tuple[DealTier, int], ...] = (
        (DealTier.LITE, 50),
        (DealTier.PLUS, 100),
        (DealTier.ULTRA, 100),
    )

    def __post_init__(self) -> None:
        integer_fields = {
            "flexible_period_buffer_days": self.flexible_period_buffer_days,
            "duration_tolerance_nights": self.duration_tolerance_nights,
        }
        if any(value < 0 for value in integer_fields.values()):
            raise InvalidEngineInputError("Configured day and duration values cannot be negative")
        if self.max_windows_per_opportunity < 1:
            raise InvalidEngineInputError("max_windows_per_opportunity must be positive")
        if self.max_concurrent_searches < 1:
            raise InvalidEngineInputError("max_concurrent_searches must be positive")
        if self.max_recommendations_per_option != 1:
            raise InvalidEngineInputError(
                "The current LuxTJ business contract returns exactly one best deal per option"
            )
        if self.leap_day_fallback_day not in {28, 29}:
            raise InvalidEngineInputError("leap_day_fallback_day must be 28 or 29")
        if not 0.0 <= self.unknown_review_confidence <= 1.0:
            raise InvalidEngineInputError("unknown_review_confidence must be between 0 and 1")
        if not 0.0 <= self.ml_blend_weight <= 1.0:
            raise InvalidEngineInputError("ml_blend_weight must be between 0 and 1")
        for collection in (self.standard_period_nights, self.family_period_nights):
            if not collection or any(nights < 1 for nights in collection):
                raise InvalidEngineInputError("Configured period nights must be positive")

    def quality_threshold(self, tier: DealTier) -> float:
        return dict(self.tier_quality_thresholds)[tier]

    def review_count_threshold(self, tier: DealTier) -> int:
        return dict(self.tier_review_count_thresholds)[tier]


DEFAULT_CONFIG = EngineConfig()
ENGINE_VERSION = "3.0.0"
FEATURE_SCHEMA_VERSION = "1.0.0"
