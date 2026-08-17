from enum import Enum


class UnsetType(Enum):
    """Distinguishes an absent field from an explicit null in partial updates."""

    UNSET = "unset"


UNSET = UnsetType.UNSET

type Patch[T] = T | UnsetType


def applied[T](value: Patch[T], current: T) -> T:
    return current if isinstance(value, UnsetType) else value
