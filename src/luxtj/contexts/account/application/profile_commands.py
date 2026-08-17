from dataclasses import dataclass
from datetime import date
from uuid import UUID

from luxtj.contexts.account.domain.patch import UNSET, Patch
from luxtj.contexts.account.domain.profile_enums import (
    BaggageStyle,
    FlightClass,
    FlightPriority,
    Gender,
    PreferredContactMethod,
    TripPace,
)
from luxtj.contexts.account.domain.profile_value_objects import CityLocation, EmergencyContact
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


@dataclass(frozen=True)
class UpdatePersonalInfoCommand:
    account_id: UUID
    first_name: Patch[str | None] = UNSET
    last_name: Patch[str | None] = UNSET
    gender: Patch[Gender | None] = UNSET
    date_of_birth: Patch[date | None] = UNSET
    nationality: Patch[str | None] = UNSET
    location: Patch[CityLocation | None] = UNSET
    language: Patch[str] = UNSET
    description: Patch[str] = UNSET
    email: Patch[str | None] = UNSET
    facebook: Patch[str | None] = UNSET
    instagram: Patch[str | None] = UNSET
    linkedin: Patch[str | None] = UNSET


@dataclass(frozen=True)
class UpdateContactInfoCommand:
    account_id: UUID
    alternative_phone: Patch[PhoneIdentity | None] = UNSET
    preferred_contact_method: Patch[PreferredContactMethod] = UNSET
    emergency_contact: Patch[EmergencyContact | None] = UNSET


@dataclass(frozen=True)
class UpdatePreferencesCommand:
    account_id: UUID
    stay_hotels: Patch[bool] = UNSET
    stay_villas: Patch[bool] = UNSET
    stay_resorts: Patch[bool] = UNSET
    stay_boutique_hotels: Patch[bool] = UNSET
    stay_cruises: Patch[bool] = UNSET
    flight_class: Patch[FlightClass] = UNSET
    flight_priority: Patch[FlightPriority] = UNSET
    trip_pace: Patch[TripPace] = UNSET
    baggage_style: Patch[BaggageStyle] = UNSET


@dataclass(frozen=True)
class UpdateDestinationsCommand:
    account_id: UUID
    countries_visited: Patch[tuple[str, ...]] = UNSET
    indian_states_visited: Patch[tuple[str, ...]] = UNSET
    places_loved: Patch[tuple[str, ...]] = UNSET
    places_recommended: Patch[tuple[str, ...]] = UNSET
    travel_moments_enjoyed: Patch[tuple[str, ...]] = UNSET


@dataclass(frozen=True)
class AddFrequentTravellerCommand:
    account_id: UUID
    first_name: str
    last_name: str | None = None
    relationship: str | None = None
    nationality: str | None = None
    gender: Gender | None = None
    birth_year: int | None = None
    birth_month: int | None = None
    passport_number: str | None = None


@dataclass(frozen=True)
class UpdateFrequentTravellerCommand:
    account_id: UUID
    traveller_id: UUID
    first_name: Patch[str] = UNSET
    last_name: Patch[str | None] = UNSET
    relationship: Patch[str | None] = UNSET
    nationality: Patch[str | None] = UNSET
    gender: Patch[Gender | None] = UNSET
    birth_year: Patch[int | None] = UNSET
    birth_month: Patch[int | None] = UNSET
    passport_number: Patch[str | None] = UNSET


@dataclass(frozen=True)
class RemoveFrequentTravellerCommand:
    account_id: UUID
    traveller_id: UUID
