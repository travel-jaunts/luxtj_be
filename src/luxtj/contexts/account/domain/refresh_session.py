from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class RefreshSession:
    id: UUID
    account_id: UUID
    token_id: str
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    rotated_at: datetime | None
    revoked_at: datetime | None
    replacement_token_id: str | None

    @classmethod
    def create(
        cls,
        *,
        account_id: UUID,
        token_id: str,
        token_hash: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> RefreshSession:
        return cls(
            id=uuid4(),
            account_id=account_id,
            token_id=token_id,
            token_hash=token_hash,
            issued_at=issued_at,
            expires_at=expires_at,
            rotated_at=None,
            revoked_at=None,
            replacement_token_id=None,
        )
