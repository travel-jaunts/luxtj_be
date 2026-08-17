from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from luxtj.contexts.account.domain.errors import InvalidProfileFieldError
from luxtj.contexts.account.domain.gallery_enums import ImageStatus
from luxtj.contexts.account.domain.patch import UNSET, Patch, applied

ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


def _validate_content_type(content_type: str) -> str:
    normalized = content_type.strip().lower()
    if normalized not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise InvalidProfileFieldError(f"unsupported image content type: {content_type}")
    return normalized


@dataclass
class GalleryImage:
    id: UUID
    account_id: UUID
    album_id: UUID
    object_key: str
    status: ImageStatus
    content_type: str
    size_bytes: int | None
    width: int | None
    height: int | None
    caption: str | None
    city_name: str | None
    latitude: float | None
    longitude: float | None
    sort_order: int
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_pending(
        cls,
        *,
        image_id: UUID,
        account_id: UUID,
        album_id: UUID,
        object_key: str,
        content_type: str,
        now: datetime,
    ) -> GalleryImage:
        return cls(
            id=image_id,
            account_id=account_id,
            album_id=album_id,
            object_key=object_key,
            status=ImageStatus.PENDING,
            content_type=_validate_content_type(content_type),
            size_bytes=None,
            width=None,
            height=None,
            caption=None,
            city_name=None,
            latitude=None,
            longitude=None,
            sort_order=0,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )

    def confirm(
        self,
        *,
        content_type: str,
        size_bytes: int,
        now: datetime,
        width: int | None = None,
        height: int | None = None,
        caption: str | None = None,
        city_name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> None:
        if size_bytes > MAX_IMAGE_SIZE_BYTES:
            raise InvalidProfileFieldError("image exceeds the 10 MB limit")
        self.content_type = _validate_content_type(content_type)
        self.size_bytes = size_bytes
        self.width = width
        self.height = height
        self.caption = caption
        self.city_name = city_name
        self.latitude = latitude
        self.longitude = longitude
        self.status = ImageStatus.READY
        self.updated_at = now

    def update(
        self,
        *,
        now: datetime,
        caption: Patch[str | None] = UNSET,
        city_name: Patch[str | None] = UNSET,
        latitude: Patch[float | None] = UNSET,
        longitude: Patch[float | None] = UNSET,
        sort_order: Patch[int] = UNSET,
    ) -> None:
        self.caption = applied(caption, self.caption)
        self.city_name = applied(city_name, self.city_name)
        self.latitude = applied(latitude, self.latitude)
        self.longitude = applied(longitude, self.longitude)
        self.sort_order = applied(sort_order, self.sort_order)
        self.updated_at = now

    def move_to_album(self, *, album_id: UUID, now: datetime) -> None:
        self.album_id = album_id
        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        self.deleted_at = now
        self.updated_at = now
