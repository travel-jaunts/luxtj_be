"""
Hard filters and validations for the recommendation engine.
Enforces business constraints, date logic, routing, and pricing rules.
"""

from datetime import date, timedelta
from enum import StrEnum

from .models import (
    BucketListRecommendationInput,
    FlightDeal,
    HotelDeal,
    HotelTier,
    RecommendationRecommendation,
)


class RejectionReason(StrEnum):
    """Structured reasons for rejecting a candidate or inventory deal."""

    INVALID_ITINERARY = "invalid_itinerary"
    INCOMPLETE_DESTINATION_COVERAGE = "incomplete_destination_coverage"
    UNAVAILABLE_HOTEL = "unavailable_hotel"
    UNAVAILABLE_FLIGHT = "unavailable_flight"
    INVALID_TRAVEL_DATES = "invalid_travel_dates"
    HOTEL_BELOW_TIER = "hotel_below_tier"
    INVALID_HOTEL = "invalid_hotel"
    INVALID_FLIGHT = "invalid_flight"
    MISSING_PRICING = "missing_pricing"
    INVALID_PRICING = "invalid_pricing"
    UNSUPPORTED_RECOMMENDATION_TIER = "unsupported_recommendation_tier"


class FilterResult:
    """Result of applying a hard filter to a recommendation candidate."""

    def __init__(
        self,
        passed: bool,
        rejection_reasons: list[RejectionReason] | None = None,
        detail: str = "",
    ) -> None:
        self.passed = passed
        self.rejection_reasons = rejection_reasons or []
        self.detail = detail

    def __repr__(self) -> str:
        return (
            f"FilterResult(passed={self.passed}, "
            f"reasons={self.rejection_reasons}, detail={self.detail!r})"
        )

    @classmethod
    def success(cls) -> FilterResult:
        return cls(passed=True)

    @classmethod
    def failure(
        cls,
        reasons: list[RejectionReason],
        detail: str,
    ) -> FilterResult:
        return cls(passed=False, rejection_reasons=reasons, detail=detail)


def validate_flight_deal(
    flight: FlightDeal,
    expected_origin: str,
    expected_destination: str,
    expected_date: date,
    is_outbound: bool,
    is_return: bool,
) -> list[RejectionReason]:
    """Validate one normalized flight deal against the expected route and date."""
    reasons: list[RejectionReason] = []

    if flight.origin.strip().upper() != expected_origin.strip().upper():
        reasons.append(RejectionReason.INVALID_FLIGHT)
    if flight.destination.strip().upper() != expected_destination.strip().upper():
        reasons.append(RejectionReason.INVALID_FLIGHT)
    if is_outbound and not flight.is_outbound:
        reasons.append(RejectionReason.INVALID_FLIGHT)
    if is_return and not flight.is_return:
        reasons.append(RejectionReason.INVALID_FLIGHT)
    if flight.departure_date != expected_date:
        reasons.append(RejectionReason.INVALID_TRAVEL_DATES)
    if flight.price is None or flight.price < 0.0:
        reasons.append(RejectionReason.MISSING_PRICING)
    if flight.duration_minutes is None or flight.duration_minutes <= 0:
        reasons.append(RejectionReason.INVALID_FLIGHT)
    if flight.stops is None or flight.stops < 0:
        reasons.append(RejectionReason.INVALID_FLIGHT)
    if not flight.flight_number or not flight.flight_number.strip():
        reasons.append(RejectionReason.INVALID_FLIGHT)

    return reasons


def validate_hotel_deal(
    hotel: HotelDeal,
    expected_destination: str,
    expected_check_in: date,
    expected_check_out: date,
    expected_tier: HotelTier,
) -> list[RejectionReason]:
    """Validate one normalized hotel deal against the expected stay and tier."""
    reasons: list[RejectionReason] = []

    if hotel.destination.strip().upper() != expected_destination.strip().upper():
        reasons.append(RejectionReason.INVALID_HOTEL)

    tier_ranks = {HotelTier.LITE: 1, HotelTier.PLUS: 2, HotelTier.ULTRA: 3}
    hotel_rank = tier_ranks.get(hotel.tier, 0)
    target_rank = tier_ranks.get(expected_tier, 0)
    if hotel_rank < target_rank:
        reasons.append(RejectionReason.HOTEL_BELOW_TIER)
    elif hotel.tier != expected_tier:
        reasons.append(RejectionReason.UNSUPPORTED_RECOMMENDATION_TIER)

    if hotel.check_in != expected_check_in or hotel.check_out != expected_check_out:
        reasons.append(RejectionReason.INVALID_TRAVEL_DATES)
    if hotel.check_in >= hotel.check_out:
        reasons.append(RejectionReason.INVALID_TRAVEL_DATES)
    if hotel.price_per_night is None or hotel.price_per_night < 0.0:
        reasons.append(RejectionReason.MISSING_PRICING)
    if hotel.rating is None or hotel.rating < 0.0 or hotel.rating > 5.0:
        reasons.append(RejectionReason.INVALID_HOTEL)
    if hotel.reviews_count < 0:
        reasons.append(RejectionReason.INVALID_HOTEL)
    if not hotel.name or not hotel.name.strip():
        reasons.append(RejectionReason.INVALID_HOTEL)

    return reasons


class HardFilter:
    """Base class for candidate hard filters."""

    def evaluate(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        target_tier: HotelTier,
    ) -> FilterResult:
        raise NotImplementedError("Subclasses must implement evaluate()")


class ItineraryValidationFilter(HardFilter):
    """Validate itinerary preservation, stay sequencing, and flight routing."""

    def evaluate(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        target_tier: HotelTier,
    ) -> FilterResult:
        expected_destinations = user_input.itinerary.destinations
        selected_hotels = candidate.hotels

        if len(selected_hotels) != len(expected_destinations):
            return FilterResult.failure(
                reasons=[RejectionReason.INCOMPLETE_DESTINATION_COVERAGE],
                detail=(
                    "Itinerary destination count modified. "
                    f"Expected {len(expected_destinations)}, got {len(selected_hotels)}."
                ),
            )

        current_expected_check_in = candidate.departure_date
        for index, (expected_destination, hotel_selection) in enumerate(
            zip(expected_destinations, selected_hotels, strict=True)
        ):
            selected_destination = hotel_selection.destination
            if selected_destination.name != expected_destination.name:
                return FilterResult.failure(
                    reasons=[RejectionReason.INVALID_ITINERARY],
                    detail=(
                        f"Destination name mismatch at index {index}. "
                        f"Expected {expected_destination.name!r}, "
                        f"got {selected_destination.name!r}."
                    ),
                )

            if selected_destination.days != expected_destination.days:
                return FilterResult.failure(
                    reasons=[RejectionReason.INVALID_ITINERARY],
                    detail=(
                        f"Destination stay days mismatch at index {index}. "
                        f"Expected {expected_destination.days}, "
                        f"got {selected_destination.days}."
                    ),
                )

            hotel_deal = hotel_selection.hotel_deal
            if hotel_deal.check_in != current_expected_check_in:
                return FilterResult.failure(
                    reasons=[RejectionReason.INVALID_TRAVEL_DATES],
                    detail=(
                        f"Hotel stay check-in index {index} mismatch. "
                        f"Expected {current_expected_check_in}, got {hotel_deal.check_in}."
                    ),
                )

            stay_nights = (hotel_deal.check_out - hotel_deal.check_in).days
            if stay_nights != expected_destination.days:
                return FilterResult.failure(
                    reasons=[RejectionReason.INVALID_ITINERARY],
                    detail=(
                        f"Hotel check-out stay nights mismatch at index {index}. "
                        f"Expected {expected_destination.days}, got {stay_nights}."
                    ),
                )

            current_expected_check_in = hotel_deal.check_out

        if current_expected_check_in != candidate.return_date:
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_TRAVEL_DATES],
                detail=(
                    f"Final hotel check-out date ({current_expected_check_in}) "
                    f"does not match return date ({candidate.return_date})."
                ),
            )

        expected_total_nights = user_input.itinerary.total_nights
        actual_total_nights = (candidate.return_date - candidate.departure_date).days
        if actual_total_nights != expected_total_nights:
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_TRAVEL_DATES],
                detail=(
                    "Trip duration nights changed. "
                    f"Expected {expected_total_nights}, got {actual_total_nights}."
                ),
            )

        outbound = candidate.flights.outbound
        return_flight = candidate.flights.return_flight
        if outbound.origin.strip().upper() != user_input.origin.strip().upper():
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_FLIGHT],
                detail=(
                    f"Outbound origin {outbound.origin!r} "
                    f"does not match user origin {user_input.origin!r}."
                ),
            )
        if (
            outbound.destination.strip().upper()
            != expected_destinations[0].name.strip().upper()
        ):
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_FLIGHT],
                detail=(
                    f"Outbound destination {outbound.destination!r} does not match "
                    f"first itinerary stop {expected_destinations[0].name!r}."
                ),
            )
        if (
            return_flight.origin.strip().upper()
            != expected_destinations[-1].name.strip().upper()
        ):
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_FLIGHT],
                detail=(
                    f"Return origin {return_flight.origin!r} does not match "
                    f"last itinerary stop {expected_destinations[-1].name!r}."
                ),
            )
        if return_flight.destination.strip().upper() != user_input.origin.strip().upper():
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_FLIGHT],
                detail=(
                    f"Return destination {return_flight.destination!r} "
                    f"does not match user origin {user_input.origin!r}."
                ),
            )

        return FilterResult.success()


class DealValidationFilter(HardFilter):
    """Apply deal-level validation to candidate flight and hotel components."""

    def evaluate(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        target_tier: HotelTier,
    ) -> FilterResult:
        reasons: list[RejectionReason] = []
        details: list[str] = []

        outbound_reasons = validate_flight_deal(
            candidate.flights.outbound,
            user_input.origin,
            user_input.itinerary.destinations[0].name,
            candidate.departure_date,
            is_outbound=True,
            is_return=False,
        )
        if outbound_reasons:
            reasons.extend(outbound_reasons)
            details.append(f"Outbound flight deal validation failed: {outbound_reasons}")

        return_reasons = validate_flight_deal(
            candidate.flights.return_flight,
            user_input.itinerary.destinations[-1].name,
            user_input.origin,
            candidate.return_date,
            is_outbound=False,
            is_return=True,
        )
        if return_reasons:
            reasons.extend(return_reasons)
            details.append(f"Return flight deal validation failed: {return_reasons}")

        current_expected_check_in = candidate.departure_date
        for index, selection in enumerate(candidate.hotels):
            expected_destination = user_input.itinerary.destinations[index]
            expected_check_out = current_expected_check_in + timedelta(
                days=expected_destination.days
            )
            hotel_reasons = validate_hotel_deal(
                selection.hotel_deal,
                expected_destination.name,
                current_expected_check_in,
                expected_check_out,
                target_tier,
            )
            if hotel_reasons:
                reasons.extend(hotel_reasons)
                details.append(
                    f"Hotel stay {index} deal validation failed: {hotel_reasons}"
                )

            current_expected_check_in = expected_check_out

        if reasons:
            return FilterResult.failure(
                reasons=list(set(reasons)),
                detail="; ".join(details),
            )

        return FilterResult.success()


class CandidatePricingFilter(HardFilter):
    """Validate that pricing is present, non-negative, and internally consistent."""

    def evaluate(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        target_tier: HotelTier,
    ) -> FilterResult:
        pricing = candidate.pricing
        if (
            pricing.flights_cost < 0.0
            or pricing.hotels_cost < 0.0
            or pricing.total_cost < 0.0
        ):
            return FilterResult.failure(
                reasons=[RejectionReason.MISSING_PRICING],
                detail=f"Negative costs detected in pricing: {pricing}",
            )

        expected_flights_cost = (
            candidate.flights.outbound.price + candidate.flights.return_flight.price
        )
        expected_hotels_cost = sum(
            selection.hotel_deal.total_price for selection in candidate.hotels
        )
        expected_total = expected_flights_cost + expected_hotels_cost
        tolerance = 0.01

        if abs(pricing.flights_cost - expected_flights_cost) > tolerance:
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_PRICING],
                detail=(
                    f"Flights cost breakdown ({pricing.flights_cost}) does not match "
                    f"flight sum ({expected_flights_cost})."
                ),
            )
        if abs(pricing.hotels_cost - expected_hotels_cost) > tolerance:
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_PRICING],
                detail=(
                    f"Hotels cost breakdown ({pricing.hotels_cost}) does not match "
                    f"hotel sum ({expected_hotels_cost})."
                ),
            )
        if abs(pricing.total_cost - expected_total) > tolerance:
            return FilterResult.failure(
                reasons=[RejectionReason.INVALID_PRICING],
                detail=(
                    f"Total cost breakdown ({pricing.total_cost}) does not match "
                    f"sum of flights and hotels ({expected_total})."
                ),
            )

        return FilterResult.success()


class HardFilterService:
    """Orchestrate candidate hard filters."""

    def __init__(self, filters: list[HardFilter] | None = None) -> None:
        self.filters = filters if filters is not None else [
            ItineraryValidationFilter(),
            DealValidationFilter(),
            CandidatePricingFilter(),
        ]

    def evaluate_candidate(
        self,
        candidate: RecommendationRecommendation,
        user_input: BucketListRecommendationInput,
        target_tier: HotelTier,
    ) -> FilterResult:
        """Run all filters and accumulate rejection reasons on failure."""
        all_passed = True
        accumulated_reasons: list[RejectionReason] = []
        accumulated_details: list[str] = []

        for candidate_filter in self.filters:
            result = candidate_filter.evaluate(candidate, user_input, target_tier)
            if not result.passed:
                all_passed = False
                accumulated_reasons.extend(result.rejection_reasons)
                if result.detail:
                    accumulated_details.append(result.detail)

        if all_passed:
            return FilterResult.success()

        return FilterResult.failure(
            reasons=list(set(accumulated_reasons)),
            detail="; ".join(accumulated_details),
        )
