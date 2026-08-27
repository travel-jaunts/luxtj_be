from dataclasses import dataclass
from uuid import UUID

from luxtj.bootstrap import config
from luxtj.contexts.account.application.ports import (
    AccountProfileRepository,
    AccountRepository,
    Clock,
    FrequentTravellerRepository,
    GalleryImageRepository,
    ObjectStorage,
)
from luxtj.contexts.account.application.profile_commands import (
    AddFrequentTravellerCommand,
    RemoveFrequentTravellerCommand,
    UpdateContactInfoCommand,
    UpdateDestinationsCommand,
    UpdateFrequentTravellerCommand,
    UpdatePersonalInfoCommand,
    UpdatePreferencesCommand,
)
from luxtj.contexts.account.domain.errors import (
    FrequentTravellerNotFoundError,
    ProfileNotFoundError,
)
from luxtj.contexts.account.domain.frequent_traveller import FrequentTraveller
from luxtj.contexts.account.domain.patch import UnsetType
from luxtj.contexts.account.domain.profile import AccountProfile
from luxtj.contexts.account.domain.profile_enums import LuxuryAccommodationTypeEnum


@dataclass(frozen=True)
class AccountProfileView:
    profile: AccountProfile
    dial_code: str
    phone_number: str
    email: str | None
    profile_picture_url: str | None
    profile_banner_url: str | None


@dataclass(frozen=True)
class LuxuryAccommodationTypeListDTO:
    accommodation_types: list[str]


class GetLuxuryAccommodationTypes:
    async def __call__(self) -> LuxuryAccommodationTypeListDTO:
        return LuxuryAccommodationTypeListDTO(
            accommodation_types=[item.value for item in LuxuryAccommodationTypeEnum]
        )


class _ProfileLoader:
    def __init__(
        self,
        *,
        profile_repository: AccountProfileRepository,
        clock: Clock,
    ) -> None:
        self._profile_repository = profile_repository
        self._clock = clock

    async def load_or_create(self, account_id: UUID) -> AccountProfile:
        profile = await self._profile_repository.get(account_id)
        if profile is None:
            profile = AccountProfile.create_default(account_id=account_id, now=self._clock.utcnow())
            await self._profile_repository.save(profile)
        return profile


class GetAccountProfile(_ProfileLoader):
    def __init__(
        self,
        *,
        profile_repository: AccountProfileRepository,
        account_repository: AccountRepository,
        image_repository: GalleryImageRepository,
        object_storage: ObjectStorage,
        clock: Clock,
    ) -> None:
        super().__init__(profile_repository=profile_repository, clock=clock)
        self._account_repository = account_repository
        self._image_repository = image_repository
        self._object_storage = object_storage

    async def __call__(self, account_id: UUID) -> AccountProfileView:
        account = await self._account_repository.get_by_id(account_id)
        if account is None:
            raise ProfileNotFoundError("account not found")
        profile = await self.load_or_create(account_id)

        picture_url = None
        if profile.profile_picture_image_id is not None:
            image = await self._image_repository.get(
                account_id=account_id, image_id=profile.profile_picture_image_id
            )
            if image is not None:
                picture_url = await self._object_storage.presigned_get_url(
                    object_key=image.object_key,
                    expires_in=config.S3_DOWNLOAD_URL_TTL_SECONDS,
                )

        banner_url = None
        if profile.profile_banner_image_id is not None:
            image = await self._image_repository.get(
                account_id=account_id, image_id=profile.profile_banner_image_id
            )
            if image is not None:
                banner_url = await self._object_storage.presigned_get_url(
                    object_key=image.object_key,
                    expires_in=config.S3_DOWNLOAD_URL_TTL_SECONDS,
                )

        return AccountProfileView(
            profile=profile,
            dial_code=account.phone_identity.dial_code,
            phone_number=account.phone_identity.phone_number,
            email=account.email,
            profile_picture_url=picture_url,
            profile_banner_url=banner_url,
        )


class UpdatePersonalInfo(_ProfileLoader):
    def __init__(
        self,
        *,
        profile_repository: AccountProfileRepository,
        account_repository: AccountRepository,
        clock: Clock,
    ) -> None:
        super().__init__(profile_repository=profile_repository, clock=clock)
        self._account_repository = account_repository

    async def __call__(self, command: UpdatePersonalInfoCommand) -> AccountProfile:
        now = self._clock.utcnow()
        profile = await self.load_or_create(command.account_id)
        profile.update_personal(
            now=now,
            first_name=command.first_name,
            last_name=command.last_name,
            gender=command.gender,
            date_of_birth=command.date_of_birth,
            nationality=command.nationality,
            location=command.location,
            language=command.language,
            description=command.description,
            facebook=command.facebook,
            instagram=command.instagram,
            linkedin=command.linkedin,
        )
        await self._profile_repository.save(profile)

        if not isinstance(command.email, UnsetType):
            account = await self._account_repository.get_by_id(command.account_id)
            if account is None:
                raise ProfileNotFoundError("account not found")
            account.change_email(command.email, now=now)
            await self._account_repository.save(account)

        return profile


class UpdateContactInfo(_ProfileLoader):
    async def __call__(self, command: UpdateContactInfoCommand) -> AccountProfile:
        profile = await self.load_or_create(command.account_id)
        profile.update_contact(
            now=self._clock.utcnow(),
            alternative_phone=command.alternative_phone,
            preferred_contact_method=command.preferred_contact_method,
            emergency_contact=command.emergency_contact,
        )
        await self._profile_repository.save(profile)
        return profile


class UpdateTravelPreferences(_ProfileLoader):
    async def __call__(self, command: UpdatePreferencesCommand) -> AccountProfile:
        profile = await self.load_or_create(command.account_id)
        profile.update_preferences(
            now=self._clock.utcnow(),
            accommodation_types=command.accommodation_types,
            flight_class=command.flight_class,
            flight_priority=command.flight_priority,
            trip_pace=command.trip_pace,
            baggage_style=command.baggage_style,
        )
        await self._profile_repository.save(profile)
        return profile


class UpdatePreferredDestinations(_ProfileLoader):
    async def __call__(self, command: UpdateDestinationsCommand) -> AccountProfile:
        profile = await self.load_or_create(command.account_id)
        profile.update_destinations(
            now=self._clock.utcnow(),
            countries_visited=command.countries_visited,
            indian_states_visited=command.indian_states_visited,
            places_loved=command.places_loved,
            places_recommended=command.places_recommended,
            travel_moments_enjoyed=command.travel_moments_enjoyed,
        )
        await self._profile_repository.save(profile)
        return profile


class ListFrequentTravellers:
    def __init__(self, *, traveller_repository: FrequentTravellerRepository) -> None:
        self._traveller_repository = traveller_repository

    async def __call__(self, account_id: UUID) -> list[FrequentTraveller]:
        return await self._traveller_repository.list_for_account(account_id)


class AddFrequentTraveller:
    def __init__(self, *, traveller_repository: FrequentTravellerRepository, clock: Clock) -> None:
        self._traveller_repository = traveller_repository
        self._clock = clock

    async def __call__(self, command: AddFrequentTravellerCommand) -> FrequentTraveller:
        traveller = FrequentTraveller.create(
            account_id=command.account_id,
            first_name=command.first_name,
            last_name=command.last_name,
            relationship=command.relationship,
            nationality=command.nationality,
            gender=command.gender,
            birth_year=command.birth_year,
            birth_month=command.birth_month,
            birth_day=command.birth_day,
            passport_number=command.passport_number,
            now=self._clock.utcnow(),
        )
        await self._traveller_repository.add(traveller)
        return traveller


class UpdateFrequentTraveller:
    def __init__(self, *, traveller_repository: FrequentTravellerRepository, clock: Clock) -> None:
        self._traveller_repository = traveller_repository
        self._clock = clock

    async def __call__(self, command: UpdateFrequentTravellerCommand) -> FrequentTraveller:
        traveller = await self._traveller_repository.get(
            account_id=command.account_id, traveller_id=command.traveller_id
        )
        if traveller is None:
            raise FrequentTravellerNotFoundError("traveller not found")
        traveller.update(
            now=self._clock.utcnow(),
            first_name=command.first_name,
            last_name=command.last_name,
            relationship=command.relationship,
            nationality=command.nationality,
            gender=command.gender,
            birth_year=command.birth_year,
            birth_month=command.birth_month,
            birth_day=command.birth_day,
            passport_number=command.passport_number,
        )
        await self._traveller_repository.save(traveller)
        return traveller


class RemoveFrequentTraveller:
    def __init__(self, *, traveller_repository: FrequentTravellerRepository) -> None:
        self._traveller_repository = traveller_repository

    async def __call__(self, command: RemoveFrequentTravellerCommand) -> None:
        removed = await self._traveller_repository.remove(
            account_id=command.account_id, traveller_id=command.traveller_id
        )
        if not removed:
            raise FrequentTravellerNotFoundError("traveller not found")
