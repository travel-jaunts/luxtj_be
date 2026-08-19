from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from luxtj.contexts.account.application.profile_use_cases import (
    AccountProfileView,
    LuxuryAccommodationTypeListDTO,
)
from luxtj.contexts.account.domain.frequent_traveller import FrequentTraveller
from luxtj.contexts.account.domain.patch import UNSET, Patch
from luxtj.contexts.account.domain.profile import AccountProfile
from luxtj.contexts.account.domain.profile_enums import (
    BaggageStyle,
    FlightClass,
    FlightPriority,
    Gender,
    LuxuryAccommodationTypeEnum,
    PreferredContactMethod,
    TripPace,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


def patched[T](body: BaseModel, field_name: str, value: T) -> Patch[T]:
    """An absent key leaves the field untouched; an explicit null clears it."""
    return value if field_name in body.model_fields_set else UNSET


class ProfileRequestBody(ApiSerializerBaseModel):
    """Rejects unknown keys: with partial updates a typo would otherwise be a silent no-op."""

    model_config = ConfigDict(extra="forbid")


# request bodies ----------------------------------------------------------------------------------
class LocationBody(ProfileRequestBody):
    city_name: str = Field(..., min_length=1, max_length=200)
    country_code: str | None = Field(None, max_length=8)
    latitude: float | None = None
    longitude: float | None = None


class EmergencyContactBody(ProfileRequestBody):
    first_name: str = Field(..., min_length=1, max_length=120)
    dial_code: str = Field(..., min_length=1, max_length=8)
    phone_number: str = Field(..., min_length=1, max_length=32)


class AlternativePhoneBody(ProfileRequestBody):
    dial_code: str = Field(..., min_length=1, max_length=8)
    phone_number: str = Field(..., min_length=1, max_length=32)


class UpdatePersonalInfoBody(ProfileRequestBody):
    first_name: str | None = Field(None, max_length=120)
    last_name: str | None = Field(None, max_length=120)
    gender: Gender | None = None
    date_of_birth: date | None = None
    nationality: str | None = Field(None, max_length=120)
    location: LocationBody | None = None
    language: str = Field("en", max_length=16)
    description: str = ""
    email: str | None = Field(None, max_length=320)
    facebook: str | None = Field(None, max_length=500)
    instagram: str | None = Field(None, max_length=500)
    linkedin: str | None = Field(None, max_length=500)


class UpdateContactInfoBody(ProfileRequestBody):
    alternative_phone: AlternativePhoneBody | None = None
    preferred_contact_method: PreferredContactMethod = PreferredContactMethod.PHONE
    emergency_contact: EmergencyContactBody | None = None


class UpdatePreferencesBody(ProfileRequestBody):
    accommodation_types: list[LuxuryAccommodationTypeEnum] = Field(
        default_factory=list,
        max_length=len(LuxuryAccommodationTypeEnum),
    )
    flight_class: FlightClass = FlightClass.ECONOMY
    flight_priority: FlightPriority = FlightPriority.BEST_VALUE
    trip_pace: TripPace = TripPace.BALANCED
    baggage_style: BaggageStyle = BaggageStyle.LIGHT_PACKER


class UpdateDestinationsBody(ProfileRequestBody):
    countries_visited: list[str] = Field(default_factory=list)
    indian_states_visited: list[str] = Field(default_factory=list)
    places_loved: list[str] = Field(default_factory=list)
    places_recommended: list[str] = Field(default_factory=list)
    travel_moments_enjoyed: list[str] = Field(default_factory=list)


class AddFrequentTravellerBody(ProfileRequestBody):
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str | None = Field(None, max_length=120)
    relationship: str | None = Field(None, max_length=60)
    nationality: str | None = Field(None, max_length=120)
    gender: Gender | None = None
    birth_year: int | None = Field(None, ge=1900, le=2200)
    birth_month: int | None = Field(None, ge=1, le=12)
    birth_day: int = Field(1, ge=1, le=31)
    passport_number: str | None = Field(None, max_length=64)


class UpdateFrequentTravellerBody(AddFrequentTravellerBody):
    traveller_id: str
    first_name: str = Field("", max_length=120)


class TravellerIdBody(ProfileRequestBody):
    traveller_id: str


class SetProfilePictureBody(ProfileRequestBody):
    image_id: str


# serializers -------------------------------------------------------------------------------------
class LocationSerializer(ApiSerializerBaseModel):
    city_name: str
    country_code: str | None
    latitude: float | None
    longitude: float | None


class PersonalInfoSerializer(ApiSerializerBaseModel):
    first_name: str | None
    last_name: str | None
    gender: Gender | None
    date_of_birth: date | None
    nationality: str | None
    location: LocationSerializer | None
    language: str
    description: str
    email: str | None
    dial_code: str
    phone_number: str
    facebook: str | None
    instagram: str | None
    linkedin: str | None


class ContactInfoSerializer(ApiSerializerBaseModel):
    email: str | None
    dial_code: str
    phone_number: str
    alternative_dial_code: str | None
    alternative_phone_number: str | None
    preferred_contact_method: PreferredContactMethod
    emergency_contact: EmergencyContactBody | None


class PreferencesSerializer(ApiSerializerBaseModel):
    accommodation_types: list[LuxuryAccommodationTypeEnum]
    flight_class: FlightClass
    flight_priority: FlightPriority
    trip_pace: TripPace
    baggage_style: BaggageStyle


class LuxuryAccommodationTypeListSerializer(ApiSerializerBaseModel):
    accommodation_types: list[str]

    @classmethod
    def from_dto(cls, dto: LuxuryAccommodationTypeListDTO) -> LuxuryAccommodationTypeListSerializer:
        return cls(accommodation_types=dto.accommodation_types)


class DestinationsSerializer(ApiSerializerBaseModel):
    countries_visited: list[str]
    indian_states_visited: list[str]
    places_loved: list[str]
    places_recommended: list[str]
    travel_moments_enjoyed: list[str]


class FrequentTravellerSerializer(ApiSerializerBaseModel):
    traveller_id: str
    first_name: str
    last_name: str | None
    relationship: str | None
    nationality: str | None
    gender: Gender | None
    birth_year: int | None
    birth_month: int | None
    birth_day: int | None
    passport_masked: str | None

    @classmethod
    def from_dto(cls, traveller: FrequentTraveller) -> FrequentTravellerSerializer:
        passport = traveller.passport_number
        return cls(
            traveller_id=str(traveller.id),
            first_name=traveller.first_name,
            last_name=traveller.last_name,
            relationship=traveller.relationship,
            nationality=traveller.nationality,
            gender=traveller.gender,
            birth_year=traveller.birth_year,
            birth_month=traveller.birth_month,
            birth_day=traveller.birth_day,
            passport_masked=f"******{passport[-4:]}" if passport else None,
        )


class FrequentTravellerListSerializer(ApiSerializerBaseModel):
    travellers: list[FrequentTravellerSerializer]

    @classmethod
    def from_dto(cls, travellers: list[FrequentTraveller]) -> FrequentTravellerListSerializer:
        return cls(travellers=[FrequentTravellerSerializer.from_dto(item) for item in travellers])


def _preferences(profile: AccountProfile) -> PreferencesSerializer:
    preferences = profile.preferences
    return PreferencesSerializer(
        accommodation_types=list(preferences.accommodation_types),
        flight_class=preferences.flight_class,
        flight_priority=preferences.flight_priority,
        trip_pace=preferences.trip_pace,
        baggage_style=preferences.baggage_style,
    )


def _destinations(profile: AccountProfile) -> DestinationsSerializer:
    destinations = profile.destinations
    return DestinationsSerializer(
        countries_visited=list(destinations.countries_visited),
        indian_states_visited=list(destinations.indian_states_visited),
        places_loved=list(destinations.places_loved),
        places_recommended=list(destinations.places_recommended),
        travel_moments_enjoyed=list(destinations.travel_moments_enjoyed),
    )


def _location(profile: AccountProfile) -> LocationSerializer | None:
    if profile.location is None:
        return None
    return LocationSerializer(
        city_name=profile.location.city_name,
        country_code=profile.location.country_code,
        latitude=profile.location.latitude,
        longitude=profile.location.longitude,
    )


def _emergency_contact(profile: AccountProfile) -> EmergencyContactBody | None:
    contact = profile.emergency_contact
    if contact is None:
        return None
    return EmergencyContactBody(
        first_name=contact.first_name,
        dial_code=contact.dial_code,
        phone_number=contact.phone_number,
    )


class AccountProfileSerializer(ApiSerializerBaseModel):
    personal: PersonalInfoSerializer
    contact: ContactInfoSerializer
    preferences: PreferencesSerializer
    destinations: DestinationsSerializer
    travellers: list[FrequentTravellerSerializer]
    tier: str
    badges: list[str]
    profile_picture_url: str | None
    completion_percentage: int

    @classmethod
    def from_dto(
        cls, view: AccountProfileView, travellers: list[FrequentTraveller]
    ) -> AccountProfileSerializer:
        profile = view.profile
        return cls(
            personal=PersonalInfoSerializer(
                first_name=profile.first_name,
                last_name=profile.last_name,
                gender=profile.gender,
                date_of_birth=profile.date_of_birth,
                nationality=profile.nationality,
                location=_location(profile),
                language=profile.language,
                description=profile.description,
                email=view.email,
                dial_code=view.dial_code,
                phone_number=view.phone_number,
                facebook=profile.social_links.facebook,
                instagram=profile.social_links.instagram,
                linkedin=profile.social_links.linkedin,
            ),
            contact=ContactInfoSerializer(
                email=view.email,
                dial_code=view.dial_code,
                phone_number=view.phone_number,
                alternative_dial_code=(
                    profile.alternative_phone.dial_code if profile.alternative_phone else None
                ),
                alternative_phone_number=(
                    profile.alternative_phone.phone_number if profile.alternative_phone else None
                ),
                preferred_contact_method=profile.preferred_contact_method,
                emergency_contact=_emergency_contact(profile),
            ),
            preferences=_preferences(profile),
            destinations=_destinations(profile),
            travellers=[FrequentTravellerSerializer.from_dto(item) for item in travellers],
            tier=profile.tier.value,
            badges=list(profile.badges),
            profile_picture_url=view.profile_picture_url,
            completion_percentage=view.completion_percentage,
        )


class ProfilePictureSerializer(ApiSerializerBaseModel):
    profile_picture_image_id: str | None

    @classmethod
    def from_dto(cls, profile: AccountProfile) -> ProfilePictureSerializer:
        return cls(
            profile_picture_image_id=(
                str(profile.profile_picture_image_id) if profile.profile_picture_image_id else None
            )
        )
