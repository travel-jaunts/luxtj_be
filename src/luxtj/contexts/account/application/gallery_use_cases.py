from dataclasses import dataclass
from uuid import UUID, uuid4

from luxtj.bootstrap import config
from luxtj.contexts.account.application.gallery_commands import (
    ConfirmImageUploadCommand,
    CreateAlbumCommand,
    GetAlbumCommand,
    ListPublicAlbumsCommand,
    RemoveAlbumCommand,
    RemoveGalleryImageCommand,
    RequestImageUploadCommand,
    SetProfilePictureCommand,
    UpdateAlbumCommand,
    UpdateGalleryImageCommand,
)
from luxtj.contexts.account.application.ports import (
    AccountProfileRepository,
    AlbumRepository,
    Clock,
    GalleryImageRepository,
    ObjectStorage,
)
from luxtj.contexts.account.domain.album import Album
from luxtj.contexts.account.domain.errors import (
    AlbumNotFoundError,
    ImageNotFoundError,
    InvalidProfileFieldError,
    InvalidProfilePictureError,
    ProfileNotFoundError,
)
from luxtj.contexts.account.domain.gallery_enums import AlbumKind, ImageStatus
from luxtj.contexts.account.domain.gallery_image import GalleryImage
from luxtj.contexts.account.domain.patch import UnsetType
from luxtj.contexts.account.domain.profile import AccountProfile


@dataclass(frozen=True)
class AlbumSummary:
    album: Album
    image_count: int
    cover_url: str | None


@dataclass(frozen=True)
class ImageView:
    image: GalleryImage
    url: str


@dataclass(frozen=True)
class AlbumDetail:
    album: Album
    images: list[ImageView]


@dataclass(frozen=True)
class UploadIntent:
    image_id: UUID
    album_id: UUID
    upload_url: str
    expires_in: int


def _object_key(*, account_id: UUID, image_id: UUID) -> str:
    return f"account/{account_id}/gallery/{image_id}"


class _GalleryService:
    def __init__(
        self,
        *,
        album_repository: AlbumRepository,
        image_repository: GalleryImageRepository,
        object_storage: ObjectStorage,
        clock: Clock,
    ) -> None:
        self._album_repository = album_repository
        self._image_repository = image_repository
        self._object_storage = object_storage
        self._clock = clock

    async def _ensure_system_albums(self, account_id: UUID) -> dict[AlbumKind, Album]:
        albums: dict[AlbumKind, Album] = {}
        for kind in (AlbumKind.DEFAULT, AlbumKind.PROFILE):
            album = await self._album_repository.get_system(account_id=account_id, kind=kind)
            if album is None:
                album = Album.create_system(
                    account_id=account_id, kind=kind, now=self._clock.utcnow()
                )
                await self._album_repository.add(album)
            albums[kind] = album
        return albums

    async def _download_url(self, object_key: str) -> str:
        return await self._object_storage.presigned_get_url(
            object_key=object_key, expires_in=config.S3_DOWNLOAD_URL_TTL_SECONDS
        )

    async def _require_album(self, *, account_id: UUID, album_id: UUID) -> Album:
        album = await self._album_repository.get(account_id=account_id, album_id=album_id)
        if album is None:
            raise AlbumNotFoundError("album not found")
        return album

    async def _require_image(self, *, account_id: UUID, image_id: UUID) -> GalleryImage:
        image = await self._image_repository.get(account_id=account_id, image_id=image_id)
        if image is None:
            raise ImageNotFoundError("image not found")
        return image


class ListAlbums(_GalleryService):
    async def __call__(self, account_id: UUID) -> list[AlbumSummary]:
        await self._ensure_system_albums(account_id)
        summaries: list[AlbumSummary] = []
        for album in await self._album_repository.list_for_account(account_id):
            cover_url = None
            if album.cover_image_id is not None:
                cover = await self._image_repository.get(
                    account_id=account_id, image_id=album.cover_image_id
                )
                if cover is not None:
                    cover_url = await self._download_url(cover.object_key)
            summaries.append(
                AlbumSummary(
                    album=album,
                    image_count=await self._image_repository.count_for_album(album_id=album.id),
                    cover_url=cover_url,
                )
            )
        return summaries


class GetAlbum(_GalleryService):
    async def __call__(self, command: GetAlbumCommand) -> AlbumDetail:
        await self._ensure_system_albums(command.account_id)
        album = await self._require_album(account_id=command.account_id, album_id=command.album_id)
        images = [
            ImageView(image=image, url=await self._download_url(image.object_key))
            for image in await self._image_repository.list_for_album(album_id=album.id)
        ]
        return AlbumDetail(album=album, images=images)


class ListPublicAlbums(_GalleryService):
    async def __call__(self, command: ListPublicAlbumsCommand) -> list[AlbumSummary]:
        albums = await self._album_repository.list_public_for_account(command.target_account_id)
        summaries: list[AlbumSummary] = []
        for album in albums:
            cover_url = None
            if album.cover_image_id is not None:
                cover = await self._image_repository.get(
                    account_id=command.target_account_id, image_id=album.cover_image_id
                )
                if cover is not None:
                    cover_url = await self._download_url(cover.object_key)
            summaries.append(
                AlbumSummary(
                    album=album,
                    image_count=await self._image_repository.count_for_album(album_id=album.id),
                    cover_url=cover_url,
                )
            )
        return summaries


class CreateAlbum(_GalleryService):
    async def __call__(self, command: CreateAlbumCommand) -> Album:
        await self._ensure_system_albums(command.account_id)
        album = Album.create(
            account_id=command.account_id,
            name=command.name,
            description=command.description,
            visibility=command.visibility,
            now=self._clock.utcnow(),
        )
        await self._album_repository.add(album)
        return album


class UpdateAlbum(_GalleryService):
    async def __call__(self, command: UpdateAlbumCommand) -> Album:
        album = await self._require_album(account_id=command.account_id, album_id=command.album_id)
        if not isinstance(command.cover_image_id, UnsetType) and command.cover_image_id is not None:
            cover = await self._require_image(
                account_id=command.account_id, image_id=command.cover_image_id
            )
            if cover.album_id != album.id:
                raise InvalidProfileFieldError("cover image must belong to the album")
        album.update(
            now=self._clock.utcnow(),
            name=command.name,
            description=command.description,
            visibility=command.visibility,
            cover_image_id=command.cover_image_id,
        )
        await self._album_repository.save(album)
        return album


class RemoveAlbum(_GalleryService):
    async def __call__(self, command: RemoveAlbumCommand) -> None:
        album = await self._require_album(account_id=command.account_id, album_id=command.album_id)
        now = self._clock.utcnow()
        album.soft_delete(now=now)
        await self._album_repository.save(album)
        await self._image_repository.soft_delete_for_album(album_id=album.id, now=now)


class RequestImageUpload(_GalleryService):
    async def __call__(self, command: RequestImageUploadCommand) -> UploadIntent:
        system_albums = await self._ensure_system_albums(command.account_id)
        if command.album_id is None:
            album = system_albums[AlbumKind.DEFAULT]
        else:
            album = await self._require_album(
                account_id=command.account_id, album_id=command.album_id
            )

        image_id = uuid4()
        image = GalleryImage.create_pending(
            image_id=image_id,
            account_id=command.account_id,
            album_id=album.id,
            object_key=_object_key(account_id=command.account_id, image_id=image_id),
            content_type=command.content_type,
            now=self._clock.utcnow(),
        )
        await self._image_repository.add(image)

        upload_url = await self._object_storage.presigned_put_url(
            object_key=image.object_key,
            content_type=image.content_type,
            expires_in=config.S3_UPLOAD_URL_TTL_SECONDS,
        )
        return UploadIntent(
            image_id=image.id,
            album_id=album.id,
            upload_url=upload_url,
            expires_in=config.S3_UPLOAD_URL_TTL_SECONDS,
        )


class ConfirmImageUpload(_GalleryService):
    async def __call__(self, command: ConfirmImageUploadCommand) -> ImageView:
        image = await self._require_image(account_id=command.account_id, image_id=command.image_id)
        metadata = await self._object_storage.head_object(object_key=image.object_key)
        if metadata is None:
            raise ImageNotFoundError("uploaded object was not found in storage")

        image.confirm(
            content_type=metadata.content_type,
            size_bytes=metadata.size_bytes,
            width=command.width,
            height=command.height,
            caption=command.caption,
            city_name=command.city_name,
            latitude=command.latitude,
            longitude=command.longitude,
            now=self._clock.utcnow(),
        )
        await self._image_repository.save(image)
        return ImageView(image=image, url=await self._download_url(image.object_key))


class UpdateGalleryImage(_GalleryService):
    async def __call__(self, command: UpdateGalleryImageCommand) -> GalleryImage:
        image = await self._require_image(account_id=command.account_id, image_id=command.image_id)
        now = self._clock.utcnow()
        if not isinstance(command.album_id, UnsetType):
            target = await self._require_album(
                account_id=command.account_id, album_id=command.album_id
            )
            image.move_to_album(album_id=target.id, now=now)
        image.update(
            now=now,
            caption=command.caption,
            city_name=command.city_name,
            latitude=command.latitude,
            longitude=command.longitude,
            sort_order=command.sort_order,
        )
        await self._image_repository.save(image)
        return image


class RemoveGalleryImage(_GalleryService):
    def __init__(
        self,
        *,
        album_repository: AlbumRepository,
        image_repository: GalleryImageRepository,
        object_storage: ObjectStorage,
        profile_repository: AccountProfileRepository,
        clock: Clock,
    ) -> None:
        super().__init__(
            album_repository=album_repository,
            image_repository=image_repository,
            object_storage=object_storage,
            clock=clock,
        )
        self._profile_repository = profile_repository

    async def __call__(self, command: RemoveGalleryImageCommand) -> None:
        image = await self._require_image(account_id=command.account_id, image_id=command.image_id)
        now = self._clock.utcnow()
        image.soft_delete(now=now)
        await self._image_repository.save(image)
        await self._album_repository.clear_cover_image(
            account_id=command.account_id, image_id=image.id
        )

        profile = await self._profile_repository.get(command.account_id)
        if profile is not None and profile.profile_picture_image_id == image.id:
            profile.clear_profile_picture(now=now)
            await self._profile_repository.save(profile)


class SetProfilePicture(_GalleryService):
    def __init__(
        self,
        *,
        album_repository: AlbumRepository,
        image_repository: GalleryImageRepository,
        object_storage: ObjectStorage,
        profile_repository: AccountProfileRepository,
        clock: Clock,
    ) -> None:
        super().__init__(
            album_repository=album_repository,
            image_repository=image_repository,
            object_storage=object_storage,
            clock=clock,
        )
        self._profile_repository = profile_repository

    async def __call__(self, command: SetProfilePictureCommand) -> AccountProfile:
        system_albums = await self._ensure_system_albums(command.account_id)
        image = await self._require_image(account_id=command.account_id, image_id=command.image_id)
        if image.status is not ImageStatus.READY:
            raise InvalidProfilePictureError("image upload has not been confirmed")
        if image.album_id != system_albums[AlbumKind.PROFILE].id:
            raise InvalidProfilePictureError("image must be in the Profile album")

        profile = await self._profile_repository.get(command.account_id)
        if profile is None:
            raise ProfileNotFoundError("profile not found")
        profile.set_profile_picture(image_id=image.id, now=self._clock.utcnow())
        await self._profile_repository.save(profile)
        return profile


class ClearProfilePicture:
    def __init__(self, *, profile_repository: AccountProfileRepository, clock: Clock) -> None:
        self._profile_repository = profile_repository
        self._clock = clock

    async def __call__(self, account_id: UUID) -> AccountProfile:
        profile = await self._profile_repository.get(account_id)
        if profile is None:
            raise ProfileNotFoundError("profile not found")
        profile.clear_profile_picture(now=self._clock.utcnow())
        await self._profile_repository.save(profile)
        return profile
