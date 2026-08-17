from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.contexts.account.domain.errors import (
    InvalidProfileFieldError,
    SystemAlbumImmutableError,
)
from luxtj.contexts.account.domain.gallery_enums import AlbumKind, AlbumVisibility
from luxtj.contexts.account.domain.patch import UNSET, Patch, applied

DEFAULT_ALBUM_NAME = "My Photos"
PROFILE_ALBUM_NAME = "Profile"


@dataclass
class Album:
    id: UUID
    account_id: UUID
    name: str
    description: str
    kind: AlbumKind
    visibility: AlbumVisibility
    cover_image_id: UUID | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        account_id: UUID,
        name: str,
        now: datetime,
        description: str = "",
        visibility: AlbumVisibility = AlbumVisibility.PRIVATE,
    ) -> Album:
        if not name.strip():
            raise InvalidProfileFieldError("album name is required")
        return cls(
            id=uuid4(),
            account_id=account_id,
            name=name.strip(),
            description=description,
            kind=AlbumKind.USER,
            visibility=visibility,
            cover_image_id=None,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def create_system(cls, *, account_id: UUID, kind: AlbumKind, now: datetime) -> Album:
        if kind is AlbumKind.USER:
            raise InvalidProfileFieldError("system albums must not use the user kind")
        return cls(
            id=uuid4(),
            account_id=account_id,
            name=DEFAULT_ALBUM_NAME if kind is AlbumKind.DEFAULT else PROFILE_ALBUM_NAME,
            description="",
            kind=kind,
            visibility=AlbumVisibility.PRIVATE,
            cover_image_id=None,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        now: datetime,
        name: Patch[str] = UNSET,
        description: Patch[str] = UNSET,
        visibility: Patch[AlbumVisibility] = UNSET,
        cover_image_id: Patch[UUID | None] = UNSET,
    ) -> None:
        if self.kind is not AlbumKind.USER and (
            name is not UNSET or description is not UNSET or visibility is not UNSET
        ):
            raise SystemAlbumImmutableError("system albums can only have their cover changed")

        resolved_name = applied(name, self.name)
        if not resolved_name.strip():
            raise InvalidProfileFieldError("album name is required")
        self.name = resolved_name.strip()
        self.description = applied(description, self.description)
        self.visibility = applied(visibility, self.visibility)
        self.cover_image_id = applied(cover_image_id, self.cover_image_id)
        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.kind is not AlbumKind.USER:
            raise SystemAlbumImmutableError("system albums cannot be deleted")
        self.deleted_at = now
        self.updated_at = now
