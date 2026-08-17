from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.contexts.account.domain.enums import AccountStatus


@dataclass(frozen=True)
class AccountStatusChange:
    id: UUID
    account_id: UUID
    actor_id: str | None
    reason: str
    from_status: AccountStatus
    to_status: AccountStatus
    changed_at: datetime

    @classmethod
    def create(
        cls,
        *,
        account_id: UUID,
        actor_id: str | None,
        reason: str,
        from_status: AccountStatus,
        to_status: AccountStatus,
        changed_at: datetime,
    ) -> AccountStatusChange:
        return cls(
            id=uuid4(),
            account_id=account_id,
            actor_id=actor_id,
            reason=reason,
            from_status=from_status,
            to_status=to_status,
            changed_at=changed_at,
        )
