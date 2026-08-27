from datetime import datetime
from typing import Annotated

import aioboto3
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.http.async_http_client import AsyncTwilioHttpClient

from luxtj.bootstrap import config
from luxtj.contexts.account.application.gallery_use_cases import (
    ClearProfileBanner,
    ClearProfilePicture,
    ConfirmImageUpload,
    CreateAlbum,
    GetAlbum,
    ListAlbums,
    ListPublicAlbums,
    RemoveAlbum,
    RemoveGalleryImage,
    RequestImageUpload,
    SetProfileBanner,
    SetProfilePicture,
    UpdateAlbum,
    UpdateGalleryImage,
)
from luxtj.contexts.account.application.ports import (
    AccountProfileRepository,
    AccountRepository,
    AccountStatusChangeRepository,
    AlbumRepository,
    Clock,
    CustomerProfileInitializer,
    FrequentTravellerRepository,
    GalleryImageRepository,
    ObjectStorage,
    OtpChallengeRepository,
    PiiCipher,
    RefreshSessionRepository,
    SmsOtpSender,
    TokenIssuer,
)
from luxtj.contexts.account.application.profile_use_cases import (
    AddFrequentTraveller,
    GetAccountProfile,
    GetLuxuryAccommodationTypes,
    ListFrequentTravellers,
    RemoveFrequentTraveller,
    UpdateContactInfo,
    UpdateFrequentTraveller,
    UpdatePersonalInfo,
    UpdatePreferredDestinations,
    UpdateTravelPreferences,
)
from luxtj.contexts.account.application.security import OtpSecurityService
from luxtj.contexts.account.application.use_cases import (
    ChangeAccountStatus,
    GetAccountStatus,
    RefreshAccountTokens,
    RequestLoginOtp,
    RequestSignupOtp,
    RevokeAccountSessions,
    RevokeRefreshSession,
    VerifyOtp,
)
from luxtj.contexts.account.infrastructure.auth.jwt_token_issuer import JoseJwtTokenIssuer
from luxtj.contexts.account.infrastructure.crypto.fernet_pii_cipher import FernetPiiCipher
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyAccountProfileRepository,
    SqlAlchemyAccountRepository,
    SqlAlchemyAccountStatusChangeRepository,
    SqlAlchemyAlbumRepository,
    SqlAlchemyFrequentTravellerRepository,
    SqlAlchemyGalleryImageRepository,
    SqlAlchemyOtpChallengeRepository,
    SqlAlchemyRefreshSessionRepository,
)
from luxtj.contexts.account.infrastructure.sms.registry_sender import RegistrySmsOtpSender
from luxtj.contexts.account.infrastructure.storage.s3_object_storage import S3ObjectStorage
from luxtj.contexts.customer.bootstrap import build_initialize_customer_profile
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
    twilio_client_handle,
)
from luxtj.utils import timeutils


class UtcClock(Clock):
    def utcnow(self) -> datetime:
        return timeutils.datetime_now()


def build_account_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AccountRepository:
    return SqlAlchemyAccountRepository(session)


def build_otp_challenge_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> OtpChallengeRepository:
    return SqlAlchemyOtpChallengeRepository(session)


def build_refresh_session_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> RefreshSessionRepository:
    return SqlAlchemyRefreshSessionRepository(session)


def build_account_status_change_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AccountStatusChangeRepository:
    return SqlAlchemyAccountStatusChangeRepository(session)


def build_clock() -> Clock:
    return UtcClock()


def build_otp_security() -> OtpSecurityService:
    return OtpSecurityService(pepper=config.AUTH_OTP_PEPPER)


def build_sms_sender(
    twilio_client: Annotated[AsyncTwilioHttpClient, Depends(twilio_client_handle)],
    http_client: Annotated[AsyncClient, Depends(http_client_handle)],
) -> SmsOtpSender:
    return RegistrySmsOtpSender(
        twilio_http_client=twilio_client,
        http_client=http_client,
        allow_test_sender=(
            config.AUTH_OTP_ALLOW_TEST_SENDER and config.ENVIRONMENT in {"development", "test"}
        ),
    )


def build_token_issuer() -> TokenIssuer:
    return JoseJwtTokenIssuer(
        keys=config.AUTH_ACCOUNT_JWT_KEYS,
        active_kid=config.AUTH_ACCOUNT_JWT_ACTIVE_KID,
        algorithms=config.AUTH_JWT_ALLOWED_ALGORITHMS,
        issuer=config.AUTH_ACCOUNT_JWT_ISSUER,
        audience=config.AUTH_ACCOUNT_JWT_AUDIENCE,
        clock_skew_seconds=config.AUTH_JWT_CLOCK_SKEW_SECONDS,
        access_ttl_seconds=config.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds=config.AUTH_REFRESH_TOKEN_TTL_SECONDS,
    )


def build_request_signup_otp(
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    sms_sender: Annotated[SmsOtpSender, Depends(build_sms_sender)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> RequestSignupOtp:
    return RequestSignupOtp(
        challenge_repository=challenge_repository,
        sms_sender=sms_sender,
        clock=clock,
        otp_security=otp_security,
        otp_ttl_seconds=config.AUTH_OTP_TTL_SECONDS,
        otp_max_attempts=config.AUTH_OTP_MAX_ATTEMPTS,
    )


def build_request_login_otp(
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    sms_sender: Annotated[SmsOtpSender, Depends(build_sms_sender)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> RequestLoginOtp:
    return RequestLoginOtp(
        challenge_repository=challenge_repository,
        sms_sender=sms_sender,
        clock=clock,
        otp_security=otp_security,
        otp_ttl_seconds=config.AUTH_OTP_TTL_SECONDS,
        otp_max_attempts=config.AUTH_OTP_MAX_ATTEMPTS,
    )


def build_verify_otp(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    customer_profile_initializer: Annotated[
        CustomerProfileInitializer,
        Depends(build_initialize_customer_profile),
    ],
    challenge_repository: Annotated[
        OtpChallengeRepository,
        Depends(build_otp_challenge_repository),
    ],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    clock: Annotated[Clock, Depends(build_clock)],
    otp_security: Annotated[OtpSecurityService, Depends(build_otp_security)],
) -> VerifyOtp:
    return VerifyOtp(
        account_repository=account_repository,
        customer_profile_initializer=customer_profile_initializer,
        challenge_repository=challenge_repository,
        refresh_session_repository=refresh_session_repository,
        token_issuer=token_issuer,
        clock=clock,
        otp_security=otp_security,
    )


def build_refresh_account_tokens(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RefreshAccountTokens:
    return RefreshAccountTokens(
        account_repository=account_repository,
        token_issuer=token_issuer,
        refresh_session_repository=refresh_session_repository,
        clock=clock,
    )


def build_revoke_refresh_session(
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    token_issuer: Annotated[TokenIssuer, Depends(build_token_issuer)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RevokeRefreshSession:
    return RevokeRefreshSession(
        refresh_session_repository=refresh_session_repository,
        token_issuer=token_issuer,
        clock=clock,
    )


def build_revoke_account_sessions(
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(build_refresh_session_repository),
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RevokeAccountSessions:
    return RevokeAccountSessions(
        refresh_session_repository=refresh_session_repository,
        clock=clock,
    )


def build_change_account_status(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    status_change_repository: Annotated[
        AccountStatusChangeRepository,
        Depends(build_account_status_change_repository),
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ChangeAccountStatus:
    return ChangeAccountStatus(
        account_repository=account_repository,
        status_change_repository=status_change_repository,
        clock=clock,
    )


def build_get_account_status(
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
) -> GetAccountStatus:
    return GetAccountStatus(account_repository=account_repository)


# profile + gallery -------------------------------------------------------------------------------
def build_pii_cipher() -> PiiCipher:
    return FernetPiiCipher(config.PII_ENCRYPTION_KEYS)


def build_object_storage() -> ObjectStorage:
    return S3ObjectStorage(
        session=aioboto3.Session(
            aws_access_key_id=config.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=config.S3_SECRET_ACCESS_KEY or None,
            region_name=config.S3_REGION,
        ),
        bucket=config.S3_BUCKET,
        endpoint_url=config.S3_ENDPOINT_URL,
        region=config.S3_REGION,
    )


def build_account_profile_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AccountProfileRepository:
    return SqlAlchemyAccountProfileRepository(session)


def build_frequent_traveller_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
    cipher: Annotated[PiiCipher, Depends(build_pii_cipher)],
) -> FrequentTravellerRepository:
    return SqlAlchemyFrequentTravellerRepository(session, cipher)


def build_album_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> AlbumRepository:
    return SqlAlchemyAlbumRepository(session)


def build_gallery_image_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> GalleryImageRepository:
    return SqlAlchemyGalleryImageRepository(session)


def build_get_account_profile(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> GetAccountProfile:
    return GetAccountProfile(
        profile_repository=profile_repository,
        account_repository=account_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_get_luxury_accommodation_types() -> GetLuxuryAccommodationTypes:
    return GetLuxuryAccommodationTypes()


def build_update_personal_info(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    account_repository: Annotated[AccountRepository, Depends(build_account_repository)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdatePersonalInfo:
    return UpdatePersonalInfo(
        profile_repository=profile_repository,
        account_repository=account_repository,
        clock=clock,
    )


def build_update_contact_info(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdateContactInfo:
    return UpdateContactInfo(profile_repository=profile_repository, clock=clock)


def build_update_travel_preferences(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdateTravelPreferences:
    return UpdateTravelPreferences(profile_repository=profile_repository, clock=clock)


def build_update_preferred_destinations(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdatePreferredDestinations:
    return UpdatePreferredDestinations(profile_repository=profile_repository, clock=clock)


def build_list_frequent_travellers(
    traveller_repository: Annotated[
        FrequentTravellerRepository, Depends(build_frequent_traveller_repository)
    ],
) -> ListFrequentTravellers:
    return ListFrequentTravellers(traveller_repository=traveller_repository)


def build_add_frequent_traveller(
    traveller_repository: Annotated[
        FrequentTravellerRepository, Depends(build_frequent_traveller_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> AddFrequentTraveller:
    return AddFrequentTraveller(traveller_repository=traveller_repository, clock=clock)


def build_update_frequent_traveller(
    traveller_repository: Annotated[
        FrequentTravellerRepository, Depends(build_frequent_traveller_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdateFrequentTraveller:
    return UpdateFrequentTraveller(traveller_repository=traveller_repository, clock=clock)


def build_remove_frequent_traveller(
    traveller_repository: Annotated[
        FrequentTravellerRepository, Depends(build_frequent_traveller_repository)
    ],
) -> RemoveFrequentTraveller:
    return RemoveFrequentTraveller(traveller_repository=traveller_repository)


def build_list_albums(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ListAlbums:
    return ListAlbums(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_get_album(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> GetAlbum:
    return GetAlbum(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_list_public_albums(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ListPublicAlbums:
    return ListPublicAlbums(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_create_album(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> CreateAlbum:
    return CreateAlbum(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_update_album(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdateAlbum:
    return UpdateAlbum(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_remove_album(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RemoveAlbum:
    return RemoveAlbum(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_request_image_upload(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RequestImageUpload:
    return RequestImageUpload(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_confirm_image_upload(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ConfirmImageUpload:
    return ConfirmImageUpload(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_update_gallery_image(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    clock: Annotated[Clock, Depends(build_clock)],
) -> UpdateGalleryImage:
    return UpdateGalleryImage(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        clock=clock,
    )


def build_remove_gallery_image(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> RemoveGalleryImage:
    return RemoveGalleryImage(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        profile_repository=profile_repository,
        clock=clock,
    )


def build_set_profile_picture(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> SetProfilePicture:
    return SetProfilePicture(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        profile_repository=profile_repository,
        clock=clock,
    )


def build_clear_profile_picture(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ClearProfilePicture:
    return ClearProfilePicture(profile_repository=profile_repository, clock=clock)


def build_set_profile_banner(
    album_repository: Annotated[AlbumRepository, Depends(build_album_repository)],
    image_repository: Annotated[GalleryImageRepository, Depends(build_gallery_image_repository)],
    object_storage: Annotated[ObjectStorage, Depends(build_object_storage)],
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> SetProfileBanner:
    return SetProfileBanner(
        album_repository=album_repository,
        image_repository=image_repository,
        object_storage=object_storage,
        profile_repository=profile_repository,
        clock=clock,
    )


def build_clear_profile_banner(
    profile_repository: Annotated[
        AccountProfileRepository, Depends(build_account_profile_repository)
    ],
    clock: Annotated[Clock, Depends(build_clock)],
) -> ClearProfileBanner:
    return ClearProfileBanner(profile_repository=profile_repository, clock=clock)
