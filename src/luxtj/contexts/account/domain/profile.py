from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from luxtj.contexts.account.domain.patch import UNSET, Patch, applied
from luxtj.contexts.account.domain.profile_enums import (
    BaggageStyle,
    FlightClass,
    FlightPriority,
    Gender,
    PreferredContactMethod,
    TripPace,
)
from luxtj.contexts.account.domain.profile_value_objects import (
    CityLocation,
    EmergencyContact,
    PreferredDestinations,
    SocialLinks,
    TravelPreferences,
)
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.customer.domain.enums import CustomerTierEnum

DEFAULT_LANGUAGE = "en"


@dataclass
class AccountProfile:
    account_id: UUID
    first_name: str | None
    last_name: str | None
    gender: Gender | None
    date_of_birth: date | None
    nationality: str | None
    location: CityLocation | None
    language: str
    description: str
    social_links: SocialLinks
    alternative_phone: PhoneIdentity | None
    preferred_contact_method: PreferredContactMethod
    emergency_contact: EmergencyContact | None
    preferences: TravelPreferences
    destinations: PreferredDestinations
    tier: CustomerTierEnum
    badges: tuple[str, ...]
    profile_picture_image_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_default(cls, *, account_id: UUID, now: datetime) -> AccountProfile:
        return cls(
            account_id=account_id,
            first_name=None,
            last_name=None,
            gender=None,
            date_of_birth=None,
            nationality=None,
            location=None,
            language=DEFAULT_LANGUAGE,
            description="",
            social_links=SocialLinks.empty(),
            alternative_phone=None,
            preferred_contact_method=PreferredContactMethod.PHONE,
            emergency_contact=None,
            preferences=TravelPreferences.default(),
            destinations=PreferredDestinations.empty(),
            tier=CustomerTierEnum.NOVUS,
            badges=(),
            profile_picture_image_id=None,
            created_at=now,
            updated_at=now,
        )

    def update_personal(
        self,
        *,
        now: datetime,
        first_name: Patch[str | None] = UNSET,
        last_name: Patch[str | None] = UNSET,
        gender: Patch[Gender | None] = UNSET,
        date_of_birth: Patch[date | None] = UNSET,
        nationality: Patch[str | None] = UNSET,
        location: Patch[CityLocation | None] = UNSET,
        language: Patch[str] = UNSET,
        description: Patch[str] = UNSET,
        facebook: Patch[str | None] = UNSET,
        instagram: Patch[str | None] = UNSET,
        linkedin: Patch[str | None] = UNSET,
    ) -> None:
        self.first_name = applied(first_name, self.first_name)
        self.last_name = applied(last_name, self.last_name)
        self.gender = applied(gender, self.gender)
        self.date_of_birth = applied(date_of_birth, self.date_of_birth)
        self.nationality = applied(nationality, self.nationality)
        self.location = applied(location, self.location)
        self.language = applied(language, self.language)
        self.description = applied(description, self.description)
        self.social_links = SocialLinks(
            facebook=applied(facebook, self.social_links.facebook),
            instagram=applied(instagram, self.social_links.instagram),
            linkedin=applied(linkedin, self.social_links.linkedin),
        )
        self.updated_at = now

    def update_contact(
        self,
        *,
        now: datetime,
        alternative_phone: Patch[PhoneIdentity | None] = UNSET,
        preferred_contact_method: Patch[PreferredContactMethod] = UNSET,
        emergency_contact: Patch[EmergencyContact | None] = UNSET,
    ) -> None:
        self.alternative_phone = applied(alternative_phone, self.alternative_phone)
        self.preferred_contact_method = applied(
            preferred_contact_method, self.preferred_contact_method
        )
        self.emergency_contact = applied(emergency_contact, self.emergency_contact)
        self.updated_at = now

    def update_preferences(
        self,
        *,
        now: datetime,
        stay_hotels: Patch[bool] = UNSET,
        stay_villas: Patch[bool] = UNSET,
        stay_resorts: Patch[bool] = UNSET,
        stay_boutique_hotels: Patch[bool] = UNSET,
        stay_cruises: Patch[bool] = UNSET,
        flight_class: Patch[FlightClass] = UNSET,
        flight_priority: Patch[FlightPriority] = UNSET,
        trip_pace: Patch[TripPace] = UNSET,
        baggage_style: Patch[BaggageStyle] = UNSET,
    ) -> None:
        current = self.preferences
        self.preferences = TravelPreferences(
            stay_hotels=applied(stay_hotels, current.stay_hotels),
            stay_villas=applied(stay_villas, current.stay_villas),
            stay_resorts=applied(stay_resorts, current.stay_resorts),
            stay_boutique_hotels=applied(stay_boutique_hotels, current.stay_boutique_hotels),
            stay_cruises=applied(stay_cruises, current.stay_cruises),
            flight_class=applied(flight_class, current.flight_class),
            flight_priority=applied(flight_priority, current.flight_priority),
            trip_pace=applied(trip_pace, current.trip_pace),
            baggage_style=applied(baggage_style, current.baggage_style),
        )
        self.updated_at = now

    def update_destinations(
        self,
        *,
        now: datetime,
        countries_visited: Patch[tuple[str, ...]] = UNSET,
        indian_states_visited: Patch[tuple[str, ...]] = UNSET,
        places_loved: Patch[tuple[str, ...]] = UNSET,
        places_recommended: Patch[tuple[str, ...]] = UNSET,
        travel_moments_enjoyed: Patch[tuple[str, ...]] = UNSET,
    ) -> None:
        current = self.destinations
        self.destinations = PreferredDestinations(
            countries_visited=applied(countries_visited, current.countries_visited),
            indian_states_visited=applied(indian_states_visited, current.indian_states_visited),
            places_loved=applied(places_loved, current.places_loved),
            places_recommended=applied(places_recommended, current.places_recommended),
            travel_moments_enjoyed=applied(travel_moments_enjoyed, current.travel_moments_enjoyed),
        )
        self.updated_at = now

    def set_profile_picture(self, *, image_id: UUID, now: datetime) -> None:
        self.profile_picture_image_id = image_id
        self.updated_at = now

    def clear_profile_picture(self, *, now: datetime) -> None:
        self.profile_picture_image_id = None
        self.updated_at = now

    def completion_percentage(self) -> int:
        """Percentage of the eleven optional profile fields the customer has filled in."""
        filled = [
            self.first_name is not None,
            self.last_name is not None,
            self.gender is not None,
            self.date_of_birth is not None,
            self.nationality is not None,
            self.location is not None,
            bool(self.description),
            not self.social_links.is_empty(),
            self.alternative_phone is not None,
            self.emergency_contact is not None,
            self.profile_picture_image_id is not None,
        ]
        return round(sum(filled) * 100 / len(filled))
