"""
Core recommendation engine orchestrator.
Manages input validation, date generation, inventory querying, candidate generation,
hard filtering, scoring, ranking, and output construction.
"""

from datetime import date, datetime

from .candidates import generate_raw_candidates
from .config import DEFAULT_CONFIG, RecommendationEngineConfig
from .date_logic import (
    calculate_hotel_stays,
    calculate_return_date,
    get_window_bounds,
    sample_dates_in_range,
)
from .exceptions import (
    InvalidItineraryError,
    InvalidPricingError,
    InvalidTravelDatesError,
    MissingInventoryError,
    UnsupportedTierError,
)
from .filters import (
    HardFilterService,
    RejectionReason,
    validate_flight_deal,
    validate_hotel_deal,
)
from .models import (
    BucketListRecommendationInput,
    BucketListRecommendationResult,
    HotelTier,
    RecommendationRecommendation,
    UnavailableResult,
    WindowRecommendations,
)
from .providers.interfaces import FlightInventoryProvider, HotelInventoryProvider
from .scoring import CompositeScorer


class BucketListRecommendationEngine:
    """Coordinate the complete bucket-list recommendation workflow."""

    def __init__(
        self,
        flight_provider: FlightInventoryProvider,
        hotel_provider: HotelInventoryProvider,
        config: RecommendationEngineConfig = DEFAULT_CONFIG,
    ) -> None:
        self.flight_provider = flight_provider
        self.hotel_provider = hotel_provider
        self.config = config
        self.filter_service = HardFilterService()
        self.scorer = CompositeScorer()

    def validate_input(self, user_input: BucketListRecommendationInput) -> None:
        """Enforce business validation on a recommendation request."""
        if not user_input.origin or not user_input.origin.strip():
            raise InvalidItineraryError("Origin airport code is missing or empty.")

        if not isinstance(user_input.reference_date, date):
            raise InvalidTravelDatesError(
                "Reference date must be a valid datetime.date object."
            )

        if not user_input.itinerary:
            raise InvalidItineraryError("Itinerary is missing.")
        if not user_input.itinerary.destinations:
            raise InvalidItineraryError(
                "Itinerary must contain at least one destination."
            )

        for index, destination in enumerate(user_input.itinerary.destinations):
            if not destination.name or not destination.name.strip():
                raise InvalidItineraryError(
                    f"Destination name at index {index} is missing or empty."
                )
            if destination.days <= 0:
                raise InvalidItineraryError(
                    f"Stay duration (days) for {destination.name!r} "
                    "must be greater than 0."
                )

        if user_input.tier is not None and user_input.tier not in {
            HotelTier.LITE,
            HotelTier.PLUS,
            HotelTier.ULTRA,
        }:
            raise UnsupportedTierError(f"Unsupported hotel tier: {user_input.tier}")

        if user_input.seasonality_data is not None:
            if not isinstance(user_input.seasonality_data, dict):
                raise InvalidItineraryError("Seasonality data must be a dictionary.")
            for destination_name, monthly_data in user_input.seasonality_data.items():
                if not isinstance(monthly_data, dict):
                    raise InvalidItineraryError(
                        f"Seasonality data for {destination_name!r} must be a dictionary."
                    )
                for month_number, coefficient in monthly_data.items():
                    if not 1 <= month_number <= 12:
                        raise InvalidTravelDatesError(
                            f"Invalid month number {month_number} in seasonality data."
                        )
                    if not 0.0 <= coefficient <= 1.0:
                        raise InvalidPricingError(
                            "Seasonality coefficient for month "
                            f"{month_number} must be between 0.0 and 1.0."
                        )

    def generate_recommendations(
        self,
        user_input: BucketListRecommendationInput,
    ) -> BucketListRecommendationResult:
        """Generate recommendations for every configured window and hotel tier."""
        self.validate_input(user_input)

        result_windows: list[WindowRecommendations] = []
        total_flights_fetched = 0
        total_hotels_fetched = 0

        for window in self.config.windows:
            start_date, end_date = get_window_bounds(
                user_input.reference_date,
                window,
            )
            sampled_dates = sample_dates_in_range(
                start_date,
                end_date,
                self.config.max_sampled_departure_dates_per_window,
            )
            valid_candidates_by_tier: dict[
                HotelTier,
                list[RecommendationRecommendation],
            ] = {
                HotelTier.LITE: [],
                HotelTier.PLUS: [],
                HotelTier.ULTRA: [],
            }
            reasons_by_tier: dict[HotelTier, set[str]] = {
                HotelTier.LITE: set(),
                HotelTier.PLUS: set(),
                HotelTier.ULTRA: set(),
            }

            for departure_date in sampled_dates:
                return_date = calculate_return_date(
                    departure_date,
                    user_input.itinerary,
                )
                first_destination = user_input.itinerary.destinations[0].name
                raw_outbound = self.flight_provider.get_flight_deals(
                    origin=user_input.origin,
                    destination=first_destination,
                    departure_date=departure_date,
                    is_outbound=True,
                    is_return=False,
                )
                last_destination = user_input.itinerary.destinations[-1].name
                raw_return = self.flight_provider.get_flight_deals(
                    origin=last_destination,
                    destination=user_input.origin,
                    departure_date=return_date,
                    is_outbound=False,
                    is_return=True,
                )
                total_flights_fetched += len(raw_outbound) + len(raw_return)

                outbound_deals = []
                for flight in raw_outbound:
                    rejection_reasons = validate_flight_deal(
                        flight,
                        user_input.origin,
                        first_destination,
                        departure_date,
                        is_outbound=True,
                        is_return=False,
                    )
                    if not rejection_reasons:
                        outbound_deals.append(flight)
                    else:
                        for reason in rejection_reasons:
                            for tier in HotelTier:
                                reasons_by_tier[tier].add(reason.value)

                return_deals = []
                for flight in raw_return:
                    rejection_reasons = validate_flight_deal(
                        flight,
                        last_destination,
                        user_input.origin,
                        return_date,
                        is_outbound=False,
                        is_return=True,
                    )
                    if not rejection_reasons:
                        return_deals.append(flight)
                    else:
                        for reason in rejection_reasons:
                            for tier in HotelTier:
                                reasons_by_tier[tier].add(reason.value)

                if not outbound_deals or not return_deals:
                    for tier in HotelTier:
                        reasons_by_tier[tier].add(
                            RejectionReason.UNAVAILABLE_FLIGHT.value
                        )

                hotel_stays = calculate_hotel_stays(
                    departure_date,
                    user_input.itinerary,
                )
                for tier in (HotelTier.LITE, HotelTier.PLUS, HotelTier.ULTRA):
                    hotels_by_destination = {}
                    any_destination_missing_hotels = False

                    for destination, check_in, check_out in hotel_stays:
                        raw_hotels = self.hotel_provider.get_hotel_deals(
                            destination=destination.name,
                            check_in=check_in,
                            check_out=check_out,
                            tier=tier,
                        )
                        total_hotels_fetched += len(raw_hotels)

                        filtered_hotels = []
                        for hotel in raw_hotels:
                            rejection_reasons = validate_hotel_deal(
                                hotel,
                                destination.name,
                                check_in,
                                check_out,
                                tier,
                            )
                            if not rejection_reasons:
                                filtered_hotels.append(hotel)
                            else:
                                for reason in rejection_reasons:
                                    reasons_by_tier[tier].add(reason.value)

                        if not filtered_hotels:
                            any_destination_missing_hotels = True
                            reasons_by_tier[tier].add(
                                RejectionReason.UNAVAILABLE_HOTEL.value
                            )

                        hotels_by_destination[destination.name] = filtered_hotels

                    if any_destination_missing_hotels:
                        continue

                    raw_candidates = generate_raw_candidates(
                        departure_date=departure_date,
                        departure_window=window.name,
                        itinerary=user_input.itinerary,
                        outbound_flights=outbound_deals,
                        return_flights=return_deals,
                        hotels_by_destination=hotels_by_destination,
                        config=self.config,
                    )
                    for candidate in raw_candidates:
                        filter_result = self.filter_service.evaluate_candidate(
                            candidate,
                            user_input,
                            tier,
                        )
                        if filter_result.passed:
                            valid_candidates_by_tier[tier].append(candidate)
                        else:
                            for reason in filter_result.rejection_reasons:
                                reasons_by_tier[tier].add(reason.value)

            tier_results: dict[
                HotelTier,
                RecommendationRecommendation | UnavailableResult,
            ] = {}
            for tier in (HotelTier.LITE, HotelTier.PLUS, HotelTier.ULTRA):
                candidates = valid_candidates_by_tier[tier]
                if not candidates:
                    reasons = sorted(reasons_by_tier[tier])
                    if not reasons:
                        reasons = [RejectionReason.UNAVAILABLE_HOTEL.value]
                    explanation = (
                        f"No valid candidates found for tier {tier.value} in window "
                        f"{window.name}. Reasons: {', '.join(reasons)}."
                    )
                    tier_results[tier] = UnavailableResult(
                        tier=tier,
                        reason_codes=reasons,
                        explanation=explanation,
                    )
                    continue

                prices = [candidate.pricing.total_cost for candidate in candidates]
                scored_candidates: list[RecommendationRecommendation] = []
                for candidate in candidates:
                    score, breakdown, explanation = self.scorer.score_candidate(
                        candidate,
                        user_input,
                        self.config,
                        context_prices=prices,
                    )
                    transparency = {
                        "outbound_flight_provider_metadata": (
                            candidate.flights.outbound.provider_metadata
                        ),
                        "return_flight_provider_metadata": (
                            candidate.flights.return_flight.provider_metadata
                        ),
                        "hotels_provider_metadata": [
                            selection.hotel_deal.provider_metadata
                            for selection in candidate.hotels
                        ],
                    }
                    scored_candidates.append(
                        RecommendationRecommendation(
                            recommendation_id=candidate.recommendation_id,
                            departure_window=candidate.departure_window,
                            departure_date=candidate.departure_date,
                            return_date=candidate.return_date,
                            flights=candidate.flights,
                            hotels=candidate.hotels,
                            pricing=candidate.pricing,
                            score=score,
                            score_breakdown=breakdown,
                            explanation=explanation,
                            provider_transparency=transparency,
                            metadata=candidate.metadata,
                        )
                    )

                def ranking_key(
                    candidate: RecommendationRecommendation,
                ) -> tuple[float, float, int, int, float, str]:
                    stops = (
                        candidate.flights.outbound.stops
                        + candidate.flights.return_flight.stops
                    )
                    duration = (
                        candidate.flights.outbound.duration_minutes
                        + candidate.flights.return_flight.duration_minutes
                    )
                    cancellation_score = candidate.score_breakdown.get(
                        "cancellation_flexibility",
                        0.0,
                    )
                    return (
                        -candidate.score,
                        candidate.pricing.total_cost,
                        stops,
                        duration,
                        -cancellation_score,
                        candidate.recommendation_id,
                    )

                scored_candidates.sort(key=ranking_key)
                tier_results[tier] = scored_candidates[0]

            result_windows.append(
                WindowRecommendations(
                    window_name=window.name,
                    departure_start=start_date,
                    departure_end=end_date,
                    lite=tier_results[HotelTier.LITE],
                    plus=tier_results[HotelTier.PLUS],
                    ultra=tier_results[HotelTier.ULTRA],
                )
            )

        if total_flights_fetched == 0 and total_hotels_fetched == 0:
            raise MissingInventoryError(
                "No inventory flights or hotels returned from external providers."
            )

        return BucketListRecommendationResult(
            windows=result_windows,
            generated_at=datetime.utcnow(),
        )


def recommend_bucket_list_deals(
    request: BucketListRecommendationInput,
    flight_provider: FlightInventoryProvider,
    hotel_provider: HotelInventoryProvider,
    config: RecommendationEngineConfig = DEFAULT_CONFIG,
) -> BucketListRecommendationResult:
    """Run the public bucket-list recommendation workflow."""
    engine = BucketListRecommendationEngine(
        flight_provider=flight_provider,
        hotel_provider=hotel_provider,
        config=config,
    )
    return engine.generate_recommendations(request)
