"""
Configuration layer for the Bucket List Recommendation Engine.
Contains definitions for recommendation windows, hotel tiers, candidate generation limits,
scoring weights, and departure date sampling rules.
"""

from dataclasses import dataclass, field


@dataclass
class WindowConfig:
    """Configuration for a specific recommendation departure window."""

    name: str
    start_month_offset: int
    end_month_offset: int


@dataclass
class ScoringWeightsConfig:
    """Candidate-scoring weights, which must sum to exactly 1.0."""

    hotel_quality: float = 0.35
    flight_convenience: float = 0.25
    package_value: float = 0.25
    cancellation_flexibility: float = 0.10
    seasonality: float = 0.05

    def __post_init__(self) -> None:
        total = (
            self.hotel_quality
            + self.flight_convenience
            + self.package_value
            + self.cancellation_flexibility
            + self.seasonality
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Scoring weights must sum to exactly 1.0, got {total}")


@dataclass
class RecommendationEngineConfig:
    """Centralized configuration for the recommendation engine."""

    windows: list[WindowConfig] = field(
        default_factory=lambda: [
            WindowConfig(name="This Month", start_month_offset=0, end_month_offset=0),
            WindowConfig(name="Months 1-3", start_month_offset=1, end_month_offset=3),
            WindowConfig(name="Months 4-6", start_month_offset=4, end_month_offset=6),
        ]
    )
    hotel_tiers: list[str] = field(default_factory=lambda: ["Lite", "Plus", "Ultra"])
    max_sampled_departure_dates_per_window: int = 5
    max_candidates_to_generate: int = 1000
    max_recommendations_per_window_and_tier: int = 5
    scoring_weights: ScoringWeightsConfig = field(default_factory=ScoringWeightsConfig)


DEFAULT_CONFIG = RecommendationEngineConfig()
