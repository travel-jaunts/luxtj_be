from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.contexts.identity.domain.errors import ValidationError


@dataclass
class Role:
    id: UUID
    name: str
    description: str
    is_active: bool
    permission_codes: set[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        name: str,
        description: str,
        permission_codes: set[str],
        now: datetime,
        is_active: bool = True,
    ) -> Role:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValidationError("Role name is required")
        if not permission_codes:
            raise ValidationError("At least one permission is required")
        return cls(
            id=uuid4(),
            name=cleaned_name,
            description=description.strip(),
            is_active=is_active,
            permission_codes=set(permission_codes),
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        permission_codes: set[str] | None = None,
        now: datetime,
    ) -> None:
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValidationError("Role name is required")
            self.name = cleaned
        if description is not None:
            self.description = description.strip()
        if is_active is not None:
            self.is_active = is_active
        if permission_codes is not None:
            if not permission_codes:
                raise ValidationError("At least one permission is required")
            self.permission_codes = set(permission_codes)
        self.updated_at = now
