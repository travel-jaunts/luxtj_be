"""
Candidate generation module.
Generates raw combinations of flight and hotel deals covering all destinations
for a given departure date and itinerary, and constructs the recommendation candidates.
"""

import hashlib
import itertools
from datetime import date

from .config import RecommendationEngineConfig
from .date_logic import calculate_return_date
from .models import (
    FlightDeal,
    FlightSelection,
    HotelDeal,
    HotelSelection,
    Itinerary,
    PricingBreakdown,
    RecommendationMetadata,
    RecommendationRecommendation,
)


def generate_candidate_id(
    departure_date: date,
    flights: FlightSelection,
    hotels: list[HotelSelection],
) -> str:
    """Generate a stable candidate ID from its selected components."""
    component_ids = [
        str(departure_date),
        flights.outbound.flight_id,
        flights.return_flight.flight_id,
    ]
    for hotel in hotels:
        component_ids.append(hotel.hotel_deal.hotel_id)

    raw_key = "-".join(component_ids).encode("utf-8")
    return f"rec-{hashlib.md5(raw_key).hexdigest()[:12]}"


def generate_raw_candidates(
    departure_date: date,
    departure_window: str,
    itinerary: Itinerary,
    outbound_flights: list[FlightDeal],
    return_flights: list[FlightDeal],
    hotels_by_destination: dict[str, list[HotelDeal]],
    config: RecommendationEngineConfig,
) -> list[RecommendationRecommendation]:
    """
    Generate complete flight-and-hotel candidates for one departure date.

    A candidate requires one outbound flight, one return flight, and one hotel
    for every itinerary destination. Incomplete combinations are not emitted.
    """
    if not outbound_flights or not return_flights:
        return []

    hotel_pools: list[list[HotelDeal]] = []
    for destination in itinerary.destinations:
        pool = hotels_by_destination.get(destination.name, [])
        if not pool:
            return []
        hotel_pools.append(pool)

    return_date = calculate_return_date(departure_date, itinerary)
    product_generator = itertools.product(outbound_flights, return_flights, *hotel_pools)
    candidates: list[RecommendationRecommendation] = []

    for count, combination in enumerate(product_generator):
        if count >= config.max_candidates_to_generate:
            break

        outbound = combination[0]
        return_flight = combination[1]
        hotels = list(combination[2:])
        flight_selection = FlightSelection(
            outbound=outbound,
            return_flight=return_flight,
        )

        hotel_selections: list[HotelSelection] = []
        hotels_cost = 0.0
        for destination, hotel_deal in zip(
            itinerary.destinations,
            hotels,
            strict=True,
        ):
            hotel_selections.append(
                HotelSelection(
                    destination=destination,
                    hotel_deal=hotel_deal,
                )
            )
            hotels_cost += hotel_deal.total_price

        flights_cost = outbound.price + return_flight.price
        pricing = PricingBreakdown(
            flights_cost=flights_cost,
            hotels_cost=hotels_cost,
            total_cost=flights_cost + hotels_cost,
        )
        recommendation_id = generate_candidate_id(
            departure_date,
            flight_selection,
            hotel_selections,
        )
        candidates.append(
            RecommendationRecommendation(
                recommendation_id=recommendation_id,
                departure_window=departure_window,
                departure_date=departure_date,
                return_date=return_date,
                flights=flight_selection,
                hotels=hotel_selections,
                pricing=pricing,
                metadata=RecommendationMetadata(departure_date=departure_date),
            )
        )

    return candidates
