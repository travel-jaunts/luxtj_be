from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.album import Album
from luxtj.contexts.account.domain.enums import AccountStatus, AuthFlowType
from luxtj.contexts.account.domain.frequent_traveller import FrequentTraveller
from luxtj.contexts.account.domain.gallery_enums import AlbumKind, AlbumVisibility, ImageStatus
from luxtj.contexts.account.domain.gallery_image import GalleryImage
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
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
from luxtj.contexts.account.domain.profile_value_objects import (
    CityLocation,
    EmergencyContact,
    PreferredDestinations,
    SocialLinks,
    TravelPreferences,
)
from luxtj.contexts.account.domain.refresh_session import RefreshSession
from luxtj.contexts.account.domain.status_change import AccountStatusChange
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.customer.domain.enums import CustomerTierEnum


class AccountAuthBase(DeclarativeBase):
    pass


class AccountRow(AccountAuthBase):
    __tablename__ = "account_accounts"
    __table_args__ = (
        UniqueConstraint("dial_code", "phone_number", name="uq_account_identity"),
        Index("ix_account_identity", "dial_code", "phone_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dial_code: Mapped[str] = mapped_column(String(8), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccountStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, account: Account) -> AccountRow:
        return cls(
            id=str(account.id),
            dial_code=account.phone_identity.dial_code,
            phone_number=account.phone_identity.phone_number,
            email=account.email,
            status=account.status.value,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    def update_from_domain(self, account: Account) -> None:
        self.email = account.email
        self.status = account.status.value
        self.updated_at = account.updated_at

    def to_domain(self) -> Account:
        return Account(
            id=UUID(self.id),
            phone_identity=PhoneIdentity(self.dial_code, self.phone_number),
            email=self.email,
            status=AccountStatus(self.status),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class OtpChallengeRow(AccountAuthBase):
    __tablename__ = "account_otp_challenges"
    __table_args__ = (
        Index(
            "ix_otp_lookup",
            "dial_code",
            "phone_number",
            "flow_type",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dial_code: Mapped[str] = mapped_column(String(8), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    flow_type: Mapped[str] = mapped_column(String(16), nullable=False)
    otp_hash: Mapped[str] = mapped_column(Text, nullable=False)
    otp_salt: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts_left: Mapped[int] = mapped_column(Integer, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, challenge: OtpChallenge) -> OtpChallengeRow:
        return cls(
            id=str(challenge.id),
            dial_code=challenge.phone_identity.dial_code,
            phone_number=challenge.phone_identity.phone_number,
            flow_type=challenge.flow_type.value,
            otp_hash=challenge.otp_hash,
            otp_salt=challenge.otp_salt,
            expires_at=challenge.expires_at,
            attempts_left=challenge.attempts_left,
            consumed_at=challenge.consumed_at,
            created_at=challenge.created_at,
        )

    def update_from_domain(self, challenge: OtpChallenge) -> None:
        self.attempts_left = challenge.attempts_left
        self.consumed_at = challenge.consumed_at

    def to_domain(self) -> OtpChallenge:
        return OtpChallenge(
            id=UUID(self.id),
            phone_identity=PhoneIdentity(self.dial_code, self.phone_number),
            flow_type=AuthFlowType(self.flow_type),
            otp_hash=self.otp_hash,
            otp_salt=self.otp_salt,
            expires_at=self.expires_at,
            attempts_left=self.attempts_left,
            consumed_at=self.consumed_at,
            created_at=self.created_at,
        )


class RefreshSessionRow(AccountAuthBase):
    __tablename__ = "account_refresh_sessions"
    __table_args__ = (
        UniqueConstraint("token_id", name="uq_account_refresh_session_token_id"),
        Index("ix_account_refresh_session_account", "account_id"),
        Index("ix_account_refresh_session_expiry", "expires_at"),
        Index("ix_account_refresh_session_revoked", "revoked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replacement_token_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    @classmethod
    def from_domain(cls, session: RefreshSession) -> RefreshSessionRow:
        return cls(
            id=str(session.id),
            account_id=str(session.account_id),
            token_id=session.token_id,
            token_hash=session.token_hash,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            rotated_at=session.rotated_at,
            revoked_at=session.revoked_at,
            replacement_token_id=session.replacement_token_id,
        )

    def to_domain(self) -> RefreshSession:
        return RefreshSession(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            token_id=self.token_id,
            token_hash=self.token_hash,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
            rotated_at=self.rotated_at,
            revoked_at=self.revoked_at,
            replacement_token_id=self.replacement_token_id,
        )


class AccountStatusChangeRow(AccountAuthBase):
    __tablename__ = "account_status_changes"
    __table_args__ = (Index("ix_account_status_changes_account", "account_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, change: AccountStatusChange) -> AccountStatusChangeRow:
        return cls(
            id=str(change.id),
            account_id=str(change.account_id),
            actor_id=change.actor_id,
            reason=change.reason,
            from_status=change.from_status.value,
            to_status=change.to_status.value,
            changed_at=change.changed_at,
        )


class AccountProfileRow(AccountAuthBase):
    __tablename__ = "account_profiles"

    account_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    facebook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    alt_dial_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    alt_phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_contact_method: Mapped[str] = mapped_column(String(16), nullable=False)
    emergency_contact_first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    emergency_contact_dial_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    emergency_contact_phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accommodation_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    flight_class: Mapped[str] = mapped_column(String(24), nullable=False)
    flight_priority: Mapped[str] = mapped_column(String(24), nullable=False)
    trip_pace: Mapped[str] = mapped_column(String(24), nullable=False)
    baggage_style: Mapped[str] = mapped_column(String(24), nullable=False)
    countries_visited: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    indian_states_visited: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    places_loved: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    places_recommended: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    travel_moments_enjoyed: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tier: Mapped[str] = mapped_column(String(16), nullable=False, default=CustomerTierEnum.NOVUS)
    badges: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    profile_picture_image_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, profile: AccountProfile) -> AccountProfileRow:
        row = cls(account_id=str(profile.account_id), created_at=profile.created_at)
        row.update_from_domain(profile)
        return row

    def update_from_domain(self, profile: AccountProfile) -> None:
        self.first_name = profile.first_name
        self.last_name = profile.last_name
        self.gender = profile.gender.value if profile.gender else None
        self.date_of_birth = profile.date_of_birth
        self.nationality = profile.nationality
        self.city_name = profile.location.city_name if profile.location else None
        self.country_code = profile.location.country_code if profile.location else None
        self.latitude = profile.location.latitude if profile.location else None
        self.longitude = profile.location.longitude if profile.location else None
        self.language = profile.language
        self.description = profile.description
        self.facebook_url = profile.social_links.facebook
        self.instagram_url = profile.social_links.instagram
        self.linkedin_url = profile.social_links.linkedin
        self.alt_dial_code = (
            profile.alternative_phone.dial_code if profile.alternative_phone else None
        )
        self.alt_phone_number = (
            profile.alternative_phone.phone_number if profile.alternative_phone else None
        )
        self.preferred_contact_method = profile.preferred_contact_method.value
        emergency = profile.emergency_contact
        self.emergency_contact_first_name = emergency.first_name if emergency else None
        self.emergency_contact_dial_code = emergency.dial_code if emergency else None
        self.emergency_contact_phone_number = emergency.phone_number if emergency else None
        preferences = profile.preferences
        self.accommodation_types = [item.value for item in preferences.accommodation_types]
        self.flight_class = preferences.flight_class.value
        self.flight_priority = preferences.flight_priority.value
        self.trip_pace = preferences.trip_pace.value
        self.baggage_style = preferences.baggage_style.value
        destinations = profile.destinations
        self.countries_visited = list(destinations.countries_visited)
        self.indian_states_visited = list(destinations.indian_states_visited)
        self.places_loved = list(destinations.places_loved)
        self.places_recommended = list(destinations.places_recommended)
        self.travel_moments_enjoyed = list(destinations.travel_moments_enjoyed)
        self.tier = profile.tier.value
        self.badges = list(profile.badges)
        self.profile_picture_image_id = (
            str(profile.profile_picture_image_id) if profile.profile_picture_image_id else None
        )
        self.updated_at = profile.updated_at

    def to_domain(self) -> AccountProfile:
        return AccountProfile(
            account_id=UUID(self.account_id),
            first_name=self.first_name,
            last_name=self.last_name,
            gender=Gender(self.gender) if self.gender else None,
            date_of_birth=self.date_of_birth,
            nationality=self.nationality,
            location=(
                CityLocation(
                    city_name=self.city_name,
                    country_code=self.country_code,
                    latitude=self.latitude,
                    longitude=self.longitude,
                )
                if self.city_name
                else None
            ),
            language=self.language,
            description=self.description,
            social_links=SocialLinks(
                facebook=self.facebook_url,
                instagram=self.instagram_url,
                linkedin=self.linkedin_url,
            ),
            alternative_phone=(
                PhoneIdentity(self.alt_dial_code, self.alt_phone_number)
                if self.alt_dial_code and self.alt_phone_number
                else None
            ),
            preferred_contact_method=PreferredContactMethod(self.preferred_contact_method),
            emergency_contact=(
                EmergencyContact(
                    first_name=self.emergency_contact_first_name,
                    dial_code=self.emergency_contact_dial_code,
                    phone_number=self.emergency_contact_phone_number,
                )
                if self.emergency_contact_first_name
                and self.emergency_contact_dial_code
                and self.emergency_contact_phone_number
                else None
            ),
            preferences=TravelPreferences(
                accommodation_types=tuple(
                    LuxuryAccommodationTypeEnum(value) for value in self.accommodation_types
                ),
                flight_class=FlightClass(self.flight_class),
                flight_priority=FlightPriority(self.flight_priority),
                trip_pace=TripPace(self.trip_pace),
                baggage_style=BaggageStyle(self.baggage_style),
            ),
            destinations=PreferredDestinations(
                countries_visited=tuple(self.countries_visited),
                indian_states_visited=tuple(self.indian_states_visited),
                places_loved=tuple(self.places_loved),
                places_recommended=tuple(self.places_recommended),
                travel_moments_enjoyed=tuple(self.travel_moments_enjoyed),
            ),
            tier=CustomerTierEnum(self.tier),
            badges=tuple(self.badges),
            profile_picture_image_id=(
                UUID(self.profile_picture_image_id) if self.profile_picture_image_id else None
            ),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class FrequentTravellerRow(AccountAuthBase):
    __tablename__ = "account_profile_travellers"
    __table_args__ = (Index("ix_account_profile_traveller_account", "account_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    relationship: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    passport_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    passport_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(
        cls, traveller: FrequentTraveller, *, passport_encrypted: str | None
    ) -> FrequentTravellerRow:
        row = cls(id=str(traveller.id), account_id=str(traveller.account_id))
        row.created_at = traveller.created_at
        row.update_from_domain(traveller, passport_encrypted=passport_encrypted)
        return row

    def update_from_domain(
        self, traveller: FrequentTraveller, *, passport_encrypted: str | None
    ) -> None:
        self.first_name = traveller.first_name
        self.last_name = traveller.last_name
        self.relationship = traveller.relationship
        self.nationality = traveller.nationality
        self.gender = traveller.gender.value if traveller.gender else None
        self.date_of_birth = traveller.date_of_birth
        self.passport_number_encrypted = passport_encrypted
        self.passport_last4 = traveller.passport_number[-4:] if traveller.passport_number else None
        self.updated_at = traveller.updated_at

    def to_domain(self, *, passport_number: str | None) -> FrequentTraveller:
        return FrequentTraveller(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            first_name=self.first_name,
            last_name=self.last_name,
            relationship=self.relationship,
            nationality=self.nationality,
            gender=Gender(self.gender) if self.gender else None,
            date_of_birth=self.date_of_birth,
            passport_number=passport_number,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class AccountAlbumRow(AccountAuthBase):
    __tablename__ = "account_albums"
    __table_args__ = (
        Index("ix_account_album_account", "account_id"),
        # Only one album per system kind; user albums are unconstrained.
        Index(
            "uq_account_album_system_kind",
            "account_id",
            "kind",
            unique=True,
            postgresql_where=text("kind <> 'user'"),
            sqlite_where=text("kind <> 'user'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False)
    cover_image_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, album: Album) -> AccountAlbumRow:
        row = cls(id=str(album.id), account_id=str(album.account_id), created_at=album.created_at)
        row.update_from_domain(album)
        return row

    def update_from_domain(self, album: Album) -> None:
        self.name = album.name
        self.description = album.description
        self.kind = album.kind.value
        self.visibility = album.visibility.value
        self.cover_image_id = str(album.cover_image_id) if album.cover_image_id else None
        self.deleted_at = album.deleted_at
        self.updated_at = album.updated_at

    def to_domain(self) -> Album:
        return Album(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            name=self.name,
            description=self.description,
            kind=AlbumKind(self.kind),
            visibility=AlbumVisibility(self.visibility),
            cover_image_id=UUID(self.cover_image_id) if self.cover_image_id else None,
            deleted_at=self.deleted_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class AccountGalleryImageRow(AccountAuthBase):
    __tablename__ = "account_gallery_images"
    __table_args__ = (
        Index("ix_account_gallery_image_account", "account_id"),
        Index("ix_account_gallery_image_album", "album_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    album_id: Mapped[str] = mapped_column(String(36), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    city_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, image: GalleryImage) -> AccountGalleryImageRow:
        row = cls(id=str(image.id), account_id=str(image.account_id), created_at=image.created_at)
        row.update_from_domain(image)
        return row

    def update_from_domain(self, image: GalleryImage) -> None:
        self.album_id = str(image.album_id)
        self.object_key = image.object_key
        self.status = image.status.value
        self.content_type = image.content_type
        self.size_bytes = image.size_bytes
        self.width = image.width
        self.height = image.height
        self.caption = image.caption
        self.city_name = image.city_name
        self.latitude = image.latitude
        self.longitude = image.longitude
        self.sort_order = image.sort_order
        self.deleted_at = image.deleted_at
        self.updated_at = image.updated_at

    def to_domain(self) -> GalleryImage:
        return GalleryImage(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            album_id=UUID(self.album_id),
            object_key=self.object_key,
            status=ImageStatus(self.status),
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            width=self.width,
            height=self.height,
            caption=self.caption,
            city_name=self.city_name,
            latitude=self.latitude,
            longitude=self.longitude,
            sort_order=self.sort_order,
            deleted_at=self.deleted_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
