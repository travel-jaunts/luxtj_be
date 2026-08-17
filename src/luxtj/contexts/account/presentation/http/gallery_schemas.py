from pydantic import Field

from luxtj.contexts.account.application.gallery_use_cases import (
    AlbumDetail,
    AlbumSummary,
    ImageView,
    UploadIntent,
)
from luxtj.contexts.account.domain.album import Album
from luxtj.contexts.account.domain.gallery_enums import AlbumKind, AlbumVisibility, ImageStatus
from luxtj.contexts.account.presentation.http.profile_schemas import ProfileRequestBody
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


# request bodies ----------------------------------------------------------------------------------
class CreateAlbumBody(ProfileRequestBody):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    visibility: AlbumVisibility = AlbumVisibility.PRIVATE


class UpdateAlbumBody(ProfileRequestBody):
    album_id: str
    name: str = Field("", max_length=200)
    description: str = ""
    visibility: AlbumVisibility = AlbumVisibility.PRIVATE
    cover_image_id: str | None = None


class AlbumIdBody(ProfileRequestBody):
    album_id: str


class TargetAccountBody(ProfileRequestBody):
    account_id: str


class RequestImageUploadBody(ProfileRequestBody):
    content_type: str = Field(..., max_length=64)
    album_id: str | None = None


class ConfirmImageUploadBody(ProfileRequestBody):
    image_id: str
    width: int | None = Field(None, ge=1)
    height: int | None = Field(None, ge=1)
    caption: str | None = None
    city_name: str | None = Field(None, max_length=200)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class UpdateImageBody(ProfileRequestBody):
    image_id: str
    caption: str | None = None
    city_name: str | None = Field(None, max_length=200)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    sort_order: int = 0
    album_id: str = ""


class ImageIdBody(ProfileRequestBody):
    image_id: str


# serializers -------------------------------------------------------------------------------------
class ImageSerializer(ApiSerializerBaseModel):
    image_id: str
    album_id: str
    status: ImageStatus
    url: str
    content_type: str
    size_bytes: int | None
    width: int | None
    height: int | None
    caption: str | None
    city_name: str | None
    latitude: float | None
    longitude: float | None
    sort_order: int

    @classmethod
    def from_dto(cls, view: ImageView) -> ImageSerializer:
        image = view.image
        return cls(
            image_id=str(image.id),
            album_id=str(image.album_id),
            status=image.status,
            url=view.url,
            content_type=image.content_type,
            size_bytes=image.size_bytes,
            width=image.width,
            height=image.height,
            caption=image.caption,
            city_name=image.city_name,
            latitude=image.latitude,
            longitude=image.longitude,
            sort_order=image.sort_order,
        )


class AlbumSerializer(ApiSerializerBaseModel):
    album_id: str
    name: str
    description: str
    kind: AlbumKind
    visibility: AlbumVisibility
    cover_image_id: str | None
    image_count: int
    cover_url: str | None

    @classmethod
    def from_dto(cls, summary: AlbumSummary) -> AlbumSerializer:
        album = summary.album
        return cls(
            album_id=str(album.id),
            name=album.name,
            description=album.description,
            kind=album.kind,
            visibility=album.visibility,
            cover_image_id=str(album.cover_image_id) if album.cover_image_id else None,
            image_count=summary.image_count,
            cover_url=summary.cover_url,
        )


class AlbumInfoSerializer(ApiSerializerBaseModel):
    album_id: str
    name: str
    description: str
    kind: AlbumKind
    visibility: AlbumVisibility
    cover_image_id: str | None

    @classmethod
    def from_dto(cls, album: Album) -> AlbumInfoSerializer:
        return cls(
            album_id=str(album.id),
            name=album.name,
            description=album.description,
            kind=album.kind,
            visibility=album.visibility,
            cover_image_id=str(album.cover_image_id) if album.cover_image_id else None,
        )


class AlbumListSerializer(ApiSerializerBaseModel):
    albums: list[AlbumSerializer]

    @classmethod
    def from_dto(cls, summaries: list[AlbumSummary]) -> AlbumListSerializer:
        return cls(albums=[AlbumSerializer.from_dto(item) for item in summaries])


class AlbumDetailSerializer(ApiSerializerBaseModel):
    album_id: str
    name: str
    description: str
    kind: AlbumKind
    visibility: AlbumVisibility
    cover_image_id: str | None
    images: list[ImageSerializer]

    @classmethod
    def from_dto(cls, detail: AlbumDetail) -> AlbumDetailSerializer:
        album = detail.album
        return cls(
            album_id=str(album.id),
            name=album.name,
            description=album.description,
            kind=album.kind,
            visibility=album.visibility,
            cover_image_id=str(album.cover_image_id) if album.cover_image_id else None,
            images=[ImageSerializer.from_dto(item) for item in detail.images],
        )


class UploadIntentSerializer(ApiSerializerBaseModel):
    image_id: str
    album_id: str
    upload_url: str
    expires_in: int

    @classmethod
    def from_dto(cls, intent: UploadIntent) -> UploadIntentSerializer:
        return cls(
            image_id=str(intent.image_id),
            album_id=str(intent.album_id),
            upload_url=intent.upload_url,
            expires_in=intent.expires_in,
        )
