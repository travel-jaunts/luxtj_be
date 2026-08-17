from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.contexts.account.domain.enums import AccountStatus
from luxtj.contexts.account.domain.errors import InvalidAccountStatusError
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


@dataclass
class Account:
    id: UUID
    phone_identity: PhoneIdentity
    email: str | None
    created_at: datetime
    updated_at: datetime
    status: AccountStatus

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
            status=AccountStatus.ACTIVE,
        )

    def suspend(self, *, now: datetime) -> None:
        if self.status == AccountStatus.DISABLED:
            raise InvalidAccountStatusError("disabled account cannot be suspended")
        if self.status == AccountStatus.SUSPENDED:
            raise InvalidAccountStatusError("account is already suspended")
        self.status = AccountStatus.SUSPENDED
        self.updated_at = now

    def disable(self, *, now: datetime) -> None:
        if self.status == AccountStatus.DISABLED:
            raise InvalidAccountStatusError("account is already disabled")
        self.status = AccountStatus.DISABLED
        self.updated_at = now

    def reenable(self, *, now: datetime) -> None:
        if self.status == AccountStatus.ACTIVE:
            raise InvalidAccountStatusError("account is already active")
        self.status = AccountStatus.ACTIVE
        self.updated_at = now

    def backfill_email_if_empty(self, email: str | None, *, now: datetime) -> bool:
        normalized_email = email.strip().lower() if email and email.strip() else None
        if not normalized_email:
            return False
        if self.email and self.email.strip():
            return False

        self.email = normalized_email
        self.updated_at = now
        return True

    def change_email(self, email: str | None, *, now: datetime) -> None:
        self.email = email.strip().lower() if email and email.strip() else None
        self.updated_at = now
