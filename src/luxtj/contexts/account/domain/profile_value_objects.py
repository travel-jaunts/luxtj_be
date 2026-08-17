from __future__ import annotations

from dataclasses import dataclass

from luxtj.contexts.account.domain.errors import InvalidProfileFieldError
from luxtj.contexts.account.domain.profile_enums import (
    BaggageStyle,
    FlightClass,
    FlightPriority,
    TripPace,
)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalized_list(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        stripped = value.strip()
        if stripped:
            seen.setdefault(stripped, None)
    return tuple(seen)


@dataclass(frozen=True)
class CityLocation:
    city_name: str
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    def __post_init__(self) -> None:
        city_name = self.city_name.strip()
        if not city_name:
            raise InvalidProfileFieldError("city name is required for a location")
        if self.latitude is not None and not -90.0 <= self.latitude <= 90.0:
            raise InvalidProfileFieldError("latitude must be between -90 and 90")
        if self.longitude is not None and not -180.0 <= self.longitude <= 180.0:
            raise InvalidProfileFieldError("longitude must be between -180 and 180")
        object.__setattr__(self, "city_name", city_name)
        object.__setattr__(self, "country_code", _optional_text(self.country_code))


@dataclass(frozen=True)
class EmergencyContact:
    first_name: str
    dial_code: str
    phone_number: str

    def __post_init__(self) -> None:
        first_name = self.first_name.strip()
        dial_code = self.dial_code.strip()
        phone_number = self.phone_number.strip()
        if not first_name or not dial_code or not phone_number:
            raise InvalidProfileFieldError(
                "emergency contact requires a first name, dial code and phone number"
            )
        object.__setattr__(self, "first_name", first_name)
        object.__setattr__(self, "dial_code", dial_code)
        object.__setattr__(self, "phone_number", phone_number)


@dataclass(frozen=True)
class SocialLinks:
    facebook: str | None = None
    instagram: str | None = None
    linkedin: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "facebook", _optional_text(self.facebook))
        object.__setattr__(self, "instagram", _optional_text(self.instagram))
        object.__setattr__(self, "linkedin", _optional_text(self.linkedin))

    @classmethod
    def empty(cls) -> SocialLinks:
        return cls()

    def is_empty(self) -> bool:
        return self.facebook is None and self.instagram is None and self.linkedin is None


@dataclass(frozen=True)
class TravelPreferences:
    stay_hotels: bool
    stay_villas: bool
    stay_resorts: bool
    stay_boutique_hotels: bool
    stay_cruises: bool
    flight_class: FlightClass
    flight_priority: FlightPriority
    trip_pace: TripPace
    baggage_style: BaggageStyle

    @classmethod
    def default(cls) -> TravelPreferences:
        return cls(
            stay_hotels=False,
            stay_villas=False,
            stay_resorts=False,
            stay_boutique_hotels=False,
            stay_cruises=False,
            flight_class=FlightClass.ECONOMY,
            flight_priority=FlightPriority.BEST_VALUE,
            trip_pace=TripPace.BALANCED,
            baggage_style=BaggageStyle.LIGHT_PACKER,
        )


@dataclass(frozen=True)
class PreferredDestinations:
    countries_visited: tuple[str, ...] = ()
    indian_states_visited: tuple[str, ...] = ()
    places_loved: tuple[str, ...] = ()
    places_recommended: tuple[str, ...] = ()
    travel_moments_enjoyed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "countries_visited",
            "indian_states_visited",
            "places_loved",
            "places_recommended",
            "travel_moments_enjoyed",
        ):
            object.__setattr__(self, field_name, _normalized_list(getattr(self, field_name)))

    @classmethod
    def empty(cls) -> PreferredDestinations:
        return cls()
