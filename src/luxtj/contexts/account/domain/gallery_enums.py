from enum import StrEnum


class AlbumVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class AlbumKind(StrEnum):
    USER = "user"
    DEFAULT = "default"
    PROFILE = "profile"


class ImageStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
