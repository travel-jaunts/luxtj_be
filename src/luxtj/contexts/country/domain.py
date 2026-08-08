"""Country catalog entity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Country:
    name: str
    iso2: str
    iso3: str
    phone_code: str
    nationality: str
    currency: str
    emoji: str
