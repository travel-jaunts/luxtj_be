from dataclasses import dataclass
from uuid import UUID

from luxtj.contexts.account.domain.gallery_enums import AlbumVisibility
from luxtj.contexts.account.domain.patch import UNSET, Patch


@dataclass(frozen=True)
class CreateAlbumCommand:
    account_id: UUID
    name: str
    description: str = ""
    visibility: AlbumVisibility = AlbumVisibility.PRIVATE


@dataclass(frozen=True)
class UpdateAlbumCommand:
    account_id: UUID
    album_id: UUID
    name: Patch[str] = UNSET
    description: Patch[str] = UNSET
    visibility: Patch[AlbumVisibility] = UNSET
    cover_image_id: Patch[UUID | None] = UNSET


@dataclass(frozen=True)
class RemoveAlbumCommand:
    account_id: UUID
    album_id: UUID


@dataclass(frozen=True)
class GetAlbumCommand:
    account_id: UUID
    album_id: UUID


@dataclass(frozen=True)
class ListPublicAlbumsCommand:
    target_account_id: UUID


@dataclass(frozen=True)
class RequestImageUploadCommand:
    account_id: UUID
    content_type: str
    album_id: UUID | None = None


@dataclass(frozen=True)
class ConfirmImageUploadCommand:
    account_id: UUID
    image_id: UUID
    width: int | None = None
    height: int | None = None
    caption: str | None = None
    city_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class UpdateGalleryImageCommand:
    account_id: UUID
    image_id: UUID
    caption: Patch[str | None] = UNSET
    city_name: Patch[str | None] = UNSET
    latitude: Patch[float | None] = UNSET
    longitude: Patch[float | None] = UNSET
    sort_order: Patch[int] = UNSET
    album_id: Patch[UUID] = UNSET


@dataclass(frozen=True)
class RemoveGalleryImageCommand:
    account_id: UUID
    image_id: UUID


@dataclass(frozen=True)
class SetProfilePictureCommand:
    account_id: UUID
    image_id: UUID
