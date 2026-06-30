from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.contexts.account.domain.value_objects import PhoneIdentity


@dataclass
class Account:
    id: UUID
    phone_identity: PhoneIdentity
    email: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        phone_identity: PhoneIdentity,
        now: datetime,
        email: str | None = None,
    ) -> Account:
        normalized_email = email.strip().lower() if email and email.strip() else None
        return cls(
            id=uuid4(),
            phone_identity=phone_identity,
            email=normalized_email,
            created_at=now,
            updated_at=now,
        )

    def backfill_email_if_empty(self, email: str | None, *, now: datetime) -> bool:
        normalized_email = email.strip().lower() if email and email.strip() else None
        if not normalized_email:
            return False
        if self.email and self.email.strip():
            return False

        self.email = normalized_email
        self.updated_at = now
        return True
