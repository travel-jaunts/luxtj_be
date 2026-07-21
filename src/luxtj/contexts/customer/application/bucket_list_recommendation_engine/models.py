"""
Business and domain models for the Bucket List Recommendation Engine.
These models represent the core business objects independent of external services,
databases, or HTTP frameworks.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class HotelTier(StrEnum):
    """Supported hotel tiers."""
    LITE = "Lite"
    PLUS = "Plus"
    ULTRA = "Ultra"


class CancellationPolicy(StrEnum):
    """Cancellation refundability policy."""
    FULLY_REFUNDABLE = "fully_refundable"
    PARTIALLY_REFUNDABLE = "partially_refundable"
    NON_REFUNDABLE = "non_refundable"


@dataclass(frozen=True)
class Destination:
    """
    Represents a single destination in the user's itinerary.
    Stay duration in nights is equal to requested days (V1 rule: requested_days == booked_hotel_nights).
    """
    name: str  # Destination name or airport code (e.g. "NRT", "Tokyo")
    days: int  # Number of days/nights to stay (must be >= 1)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Destination name cannot be empty")
        if self.days <= 0:
            raise ValueError(f"Stay duration (days) must be at least 1, got {self.days}")


@dataclass(frozen=True)
class Itinerary:
    """
    Represents a finalized itinerary containing an ordered sequence of destinations.
    The itinerary is immutable; order, names, and durations must be preserved.
    """
    destinations: list[Destination]

    def __post_init__(self) -> None:
        if not self.destinations:
            raise ValueError("Itinerary must contain at least one destination")

    @property
    def total_nights(self) -> int:
        """Total nights for the trip, calculated as sum of destination stay durations."""
        return sum(d.days for d in self.destinations)


@dataclass(frozen=True)
class FlightDeal:
    """Represents a normalized flight deal candidate."""
    flight_id: str
    origin: str
    destination: str
    departure_date: date
    price: float
    carrier: str
    flight_number: str
    is_outbound: bool
    is_return: bool
    stops: int = 0
    duration_minutes: int = 0
    cancellation_policy: CancellationPolicy = CancellationPolicy.NON_REFUNDABLE
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HotelDeal:
    """Represents a normalized hotel deal candidate matching a specific tier."""
    hotel_id: str
    name: str
    destination: str
    tier: HotelTier
    check_in: date
    check_out: date
    price_per_night: float
    rating: float | None = None
    reviews_count: int = 0
    cancellation_policy: CancellationPolicy = CancellationPolicy.NON_REFUNDABLE
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_price(self) -> float:
        """Calculates total price based on duration of stay."""
        nights = (self.check_out - self.check_in).days
        return self.price_per_night * nights


@dataclass(frozen=True)
class BucketListRecommendationInput:
    """
    Business input model for generating recommendations.
    Provides all necessary data points without tying to any web request structure.
    """
    origin: str  # Origin airport code/city (e.g. "LAX")
    reference_date: date  # Reference date from which windows and departure dates are calculated
    itinerary: Itinerary
    tier: HotelTier | None = None  # Optional preferred tier (Lite, Plus, Ultra)
    seasonality_data: dict[str, dict[int, float]] | None = None  # Destination -> Month (1-12) -> Score (0.0 to 1.0)

    def __post_init__(self) -> None:
        if not self.origin or not self.origin.strip():
            raise ValueError("Origin cannot be empty")


@dataclass(frozen=True)
class HotelSelection:
    """Represents the selected hotel deal for a destination in the itinerary."""
    destination: Destination
    hotel_deal: HotelDeal


@dataclass(frozen=True)
class FlightSelection:
    """Represents the outbound and return flights selected for the recommendation."""
    outbound: FlightDeal
    return_flight: FlightDeal


@dataclass(frozen=True)
class PricingBreakdown:
    """Breakdown of costs for the recommendation."""
    flights_cost: float
    hotels_cost: float
    total_cost: float


@dataclass(frozen=True)
class RecommendationMetadata:
    """Metadata about the generated recommendation."""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "3.0.0"
    departure_date: date = field(default=date.min)


@dataclass(frozen=True)
class RecommendationRecommendation:
    """
    A single generated and validated recommendation candidate.
    Includes selected flights, hotels, total price, score, and explanation.
    """
    recommendation_id: str
    departure_window: str
    departure_date: date
    return_date: date
    flights: FlightSelection
    hotels: list[HotelSelection]  # Order corresponds to destinations in the itinerary
    pricing: PricingBreakdown
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    provider_transparency: dict[str, Any] = field(default_factory=dict)
    metadata: RecommendationMetadata = field(default_factory=RecommendationMetadata)

    @property
    def travel_dates(self) -> dict[str, date]:
        """Convenience property returning travel dates dict."""
        return {"departure_date": self.departure_date, "return_date": self.return_date}

    @property
    def hotel_pricing(self) -> float:
        """Convenience property for hotel pricing."""
        return self.pricing.hotels_cost

    @property
    def flight_pricing(self) -> float:
        """Convenience property for flight pricing."""
        return self.pricing.flights_cost

    @property
    def package_pricing(self) -> float:
        """Convenience property for total package pricing."""
        return self.pricing.total_cost


@dataclass(frozen=True)
class UnavailableResult:
    """Represents an unavailable recommendation with structured rejection reason codes."""
    tier: HotelTier
    reason_codes: list[str]
    explanation: str


@dataclass(frozen=True)
class WindowRecommendations:
    """Group of recommendations for a specific time window, covering Lite, Plus, and Ultra tiers."""
    window_name: str
    departure_start: date
    departure_end: date
    lite: RecommendationRecommendation | UnavailableResult
    plus: RecommendationRecommendation | UnavailableResult
    ultra: RecommendationRecommendation | UnavailableResult


@dataclass(frozen=True)
class BucketListRecommendationResult:
    """
    The final recommendation output for the public entry point.
    Contains recommendations grouped by departure windows, covering all tiers, and metadata.
    """
    windows: list[WindowRecommendations]
    generated_at: datetime = field(default_factory=datetime.utcnow)
