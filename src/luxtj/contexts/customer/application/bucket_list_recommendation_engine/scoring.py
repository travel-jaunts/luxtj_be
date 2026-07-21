"""
Complete scoring engine implementation for the Bucket List Recommendation Engine.
Computes composite scoring for hotel quality, flight convenience, package value,
cancellation flexibility, and seasonality.
"""

from abc import ABC, abstractmethod
from math import log10

from .config import RecommendationEngineConfig
from .models import (
    BucketListRecommendationInput,
    CancellationPolicy,
    RecommendationRecommendation,
)


class ScoringComponent(ABC):
    """Abstract base class for an individual scoring dimension."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique scoring-component name."""
        pass

    @abstractmethod
    def score(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> float:
        """Calculate a normalized score between 0.0 and 1.0."""
        pass


class HotelQualityScorer(ScoringComponent):
    """Evaluate hotel ratings, review evidence, and rating consistency."""

    @property
    def name(self) -> str:
        return "hotel_quality"

    def score(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> float:
        ratings = [
            selection.hotel_deal.rating
            for selection in candidate.hotels
            if selection.hotel_deal.rating is not None
        ]

        if not ratings:
            rating_score = 0.6
            consistency_score = 1.0
        else:
            average_rating = sum(ratings) / len(ratings)
            rating_score = average_rating / 5.0
            max_difference = max(ratings) - min(ratings)
            consistency_score = 1.0 - max_difference / 5.0

        review_scores = []
        for selection in candidate.hotels:
            review_count = selection.hotel_deal.reviews_count
            if review_count <= 0:
                review_scores.append(0.0)
            else:
                review_scores.append(min(1.0, log10(1 + review_count) / log10(500)))

        reviews_score = sum(review_scores) / len(review_scores) if review_scores else 0.0
        quality_score = (
            0.5 * rating_score
            + 0.25 * reviews_score
            + 0.25 * consistency_score
        )
        return max(0.0, min(1.0, quality_score))


class FlightConvenienceScorer(ScoringComponent):
    """Evaluate total stops and total outbound-plus-return duration."""

    @property
    def name(self) -> str:
        return "flight_convenience"

    def score(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> float:
        outbound = candidate.flights.outbound
        return_flight = candidate.flights.return_flight

        total_stops = outbound.stops + return_flight.stops
        stops_score = max(0.0, 1.0 - total_stops * 0.25)

        total_duration = outbound.duration_minutes + return_flight.duration_minutes
        if total_duration <= 0:
            duration_score = 0.5
        else:
            duration_score = max(
                0.0,
                1.0 - max(0.0, total_duration - 600.0) / 1800.0,
            )

        return 0.5 * stops_score + 0.5 * duration_score


class PackageValueScorer(ScoringComponent):
    """Evaluate relative package cost within the same window and hotel tier."""

    @property
    def name(self) -> str:
        return "package_value"

    def score(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> float:
        if not context_prices or len(context_prices) <= 1:
            return 1.0

        minimum_price = min(context_prices)
        maximum_price = max(context_prices)
        if abs(maximum_price - minimum_price) < 0.01:
            return 1.0

        value_score = (maximum_price - candidate.pricing.total_cost) / (
            maximum_price - minimum_price
        )
        return max(0.0, min(1.0, value_score))


class CancellationFlexibilityScorer(ScoringComponent):
    """Evaluate cancellation policies for all selected flights and hotels."""

    @property
    def name(self) -> str:
        return "cancellation_flexibility"

    def _get_policy_score(self, policy: CancellationPolicy) -> float:
        if policy == CancellationPolicy.FULLY_REFUNDABLE:
            return 1.0
        if policy == CancellationPolicy.PARTIALLY_REFUNDABLE:
            return 0.5
        return 0.0

    def score(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> float:
        scores = [
            self._get_policy_score(candidate.flights.outbound.cancellation_policy),
            self._get_policy_score(candidate.flights.return_flight.cancellation_policy),
        ]
        scores.extend(
            self._get_policy_score(selection.hotel_deal.cancellation_policy)
            for selection in candidate.hotels
        )
        return sum(scores) / len(scores) if scores else 0.0


class SeasonalityScorer(ScoringComponent):
    """Evaluate destination seasonality for each selected hotel stay."""

    @property
    def name(self) -> str:
        return "seasonality"

    def score(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> float:
        seasonality_data = user_input.seasonality_data
        if not seasonality_data:
            return 0.5

        scores = []
        for selection in candidate.hotels:
            destination_data = seasonality_data.get(selection.destination.name, {})
            scores.append(destination_data.get(selection.hotel_deal.check_in.month, 0.5))

        return sum(scores) / len(scores) if scores else 0.5


class CompositeScorer:
    """Combine individual scoring components using configured weights."""

    def __init__(self, components: list[ScoringComponent] | None = None) -> None:
        self.components = components if components is not None else [
            HotelQualityScorer(),
            FlightConvenienceScorer(),
            PackageValueScorer(),
            CancellationFlexibilityScorer(),
            SeasonalityScorer(),
        ]

    def score_candidate(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        config: RecommendationEngineConfig,
        context_prices: list[float] | None = None,
    ) -> tuple[float, dict[str, float], str]:
        """Calculate the composite score, component breakdown, and explanation."""
        weights = config.scoring_weights
        weights_by_component = {
            "hotel_quality": weights.hotel_quality,
            "flight_convenience": weights.flight_convenience,
            "package_value": weights.package_value,
            "cancellation_flexibility": weights.cancellation_flexibility,
            "seasonality": weights.seasonality,
        }

        score_breakdown: dict[str, float] = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for component in self.components:
            weight = weights_by_component.get(component.name, 0.0)
            raw_score = component.score(
                candidate,
                user_input,
                config,
                context_prices,
            )
            normalized_score = max(0.0, min(1.0, raw_score))
            score_breakdown[component.name] = round(normalized_score, 4)
            weighted_sum += normalized_score * weight
            total_weight += weight

        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        final_score = round(final_score, 4)
        explanation_parts = [f"Composite Score: {final_score:.2f}"]
        for name, component_score in score_breakdown.items():
            display_name = name.replace("_", " ").title()
            explanation_parts.append(f"{display_name}: {component_score:.2f}")

        return final_score, score_breakdown, " | ".join(explanation_parts)
