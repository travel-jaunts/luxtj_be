from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from luxtj.contexts.account.domain.errors import InvalidProfileFieldError
from luxtj.contexts.account.domain.patch import UNSET, Patch, applied
from luxtj.contexts.account.domain.profile_enums import Gender


def _birth_date(*, birth_year: int, birth_month: int, birth_day: int, now: datetime) -> date:
    if not 1 <= birth_month <= 12:
        raise InvalidProfileFieldError("birth month must be between 1 and 12")
    try:
        value = date(birth_year, birth_month, birth_day)
    except ValueError as exc:
        raise InvalidProfileFieldError("invalid birth date") from exc
    if value > now.date():
        raise InvalidProfileFieldError("birth date cannot be in the future")
    return value


@dataclass
class FrequentTraveller:
    id: UUID
    account_id: UUID
    first_name: str
    last_name: str | None
    relationship: str | None
    nationality: str | None
    gender: Gender | None
    date_of_birth: date | None
    passport_number: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def birth_year(self) -> int | None:
        return self.date_of_birth.year if self.date_of_birth else None

    @property
    def birth_month(self) -> int | None:
        return self.date_of_birth.month if self.date_of_birth else None

    @property
    def birth_day(self) -> int | None:
        return self.date_of_birth.day if self.date_of_birth else None

    @classmethod
    def create(
        cls,
        *,
        account_id: UUID,
        first_name: str,
        now: datetime,
        last_name: str | None = None,
        relationship: str | None = None,
        nationality: str | None = None,
        gender: Gender | None = None,
        birth_year: int | None = None,
        birth_month: int | None = None,
        birth_day: int = 1,
        passport_number: str | None = None,
    ) -> FrequentTraveller:
        if not first_name.strip():
            raise InvalidProfileFieldError("traveller first name is required")
        return cls(
            id=uuid4(),
            account_id=account_id,
            first_name=first_name.strip(),
            last_name=last_name,
            relationship=relationship,
            nationality=nationality,
            gender=gender,
            date_of_birth=_resolve_birth_date(birth_year, birth_month, birth_day, now),
            passport_number=passport_number,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        now: datetime,
        first_name: Patch[str] = UNSET,
        last_name: Patch[str | None] = UNSET,
        relationship: Patch[str | None] = UNSET,
        nationality: Patch[str | None] = UNSET,
        gender: Patch[Gender | None] = UNSET,
        birth_year: Patch[int | None] = UNSET,
        birth_month: Patch[int | None] = UNSET,
        birth_day: Patch[int | None] = UNSET,
        passport_number: Patch[str | None] = UNSET,
    ) -> None:
        resolved_first_name = applied(first_name, self.first_name)
        if not resolved_first_name.strip():
            raise InvalidProfileFieldError("traveller first name is required")
        self.first_name = resolved_first_name.strip()
        self.last_name = applied(last_name, self.last_name)
        self.relationship = applied(relationship, self.relationship)
        self.nationality = applied(nationality, self.nationality)
        self.gender = applied(gender, self.gender)
        self.passport_number = applied(passport_number, self.passport_number)
        resolved_birth_year = applied(birth_year, self.birth_year)
        resolved_birth_month = applied(birth_month, self.birth_month)
        resolved_birth_day = applied(birth_day, self.birth_day)
        if birth_day is UNSET and (birth_year is not UNSET or birth_month is not UNSET):
            resolved_birth_day = 1
        self.date_of_birth = _resolve_birth_date(
            resolved_birth_year, resolved_birth_month, resolved_birth_day, now
        )
        self.updated_at = now


def _resolve_birth_date(
    birth_year: int | None, birth_month: int | None, birth_day: int | None, now: datetime
) -> date | None:
    if birth_year is None and birth_month is None:
        return None
    if birth_year is None or birth_month is None:
        raise InvalidProfileFieldError("birth month and birth year must be provided together")
    if birth_day is None:
        raise InvalidProfileFieldError("birth day must be provided with birth month and birth year")
    return _birth_date(birth_year=birth_year, birth_month=birth_month, birth_day=birth_day, now=now)
