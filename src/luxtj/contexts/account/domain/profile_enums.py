from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class PreferredContactMethod(StrEnum):
    EMAIL = "email"
    PHONE = "phone"


class FlightClass(StrEnum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class FlightPriority(StrEnum):
    BEST_VALUE = "best_value"
    DIRECT_FLIGHT = "direct_flight"
    FLEXIBLE_TICKETS = "flexible_tickets"
    BETTER_TIMINGS = "better_timings"


class TripPace(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    FAST_PACED = "fast_paced"


class BaggageStyle(StrEnum):
    LIGHT_PACKER = "light_packer"
    CHECKED_BAGGAGE_OKAY = "checked_baggage_okay"


class LuxuryAccommodationTypeEnum(StrEnum):
    URBAN_LUXURY_HOTELS = "Urban Luxury Hotels"
    LUXURY_RESORTS = "Luxury Resorts"
    HERITAGE_AND_PALACE_HOTELS = "Heritage & Palace Hotels"
    BOUTIQUE_LUXURY_HOTELS = "Boutique Luxury Hotels"
    PRIVATE_VILLAS_AND_LUXURY_RENTALS = "Private Villas & Luxury Rentals"
    ECO_LUXURY_LODGES = "Eco-Luxury Lodges"
    SAFARI_LODGES = "Safari Lodges (Wildlife Luxury Stays)"
    GLAMPING = "Glamping (Luxury Camping)"
    LUXURY_CRUISES_AND_FLOATING_HOTELS = "Luxury Cruises / Floating Hotels"
