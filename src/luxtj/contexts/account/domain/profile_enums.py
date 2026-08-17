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
