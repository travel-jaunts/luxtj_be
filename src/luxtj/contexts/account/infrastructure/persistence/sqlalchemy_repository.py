from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.refresh_session import RefreshSession
from luxtj.contexts.account.domain.status_change import AccountStatusChange
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_models import (
    AccountRow,
    AccountStatusChangeRow,
    OtpChallengeRow,
    RefreshSessionRow,
)


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: Account) -> None:
        self._session.add(AccountRow.from_domain(account))

    async def get_by_id(self, account_id: UUID) -> Account | None:
        row = await self._session.scalar(select(AccountRow).where(AccountRow.id == str(account_id)))
        return row.to_domain() if row is not None else None

    async def get_by_phone_identity(self, phone_identity: PhoneIdentity) -> Account | None:
        row = await self._session.scalar(
            select(AccountRow).where(
                AccountRow.dial_code == phone_identity.dial_code,
                AccountRow.phone_number == phone_identity.phone_number,
            )
        )
        return row.to_domain() if row is not None else None

    async def save(self, account: Account) -> None:
        row = await self._session.scalar(select(AccountRow).where(AccountRow.id == str(account.id)))
        if row is None:
            self._session.add(AccountRow.from_domain(account))
            return
        row.update_from_domain(account)


class SqlAlchemyOtpChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, challenge: OtpChallenge) -> None:
        self._session.add(OtpChallengeRow.from_domain(challenge))

    async def find_latest_for_flow(
        self,
        *,
        phone_identity: PhoneIdentity,
        flow_type: AuthFlowType,
    ) -> OtpChallenge | None:
        row = await self._session.scalar(
            select(OtpChallengeRow)
            .where(
                OtpChallengeRow.dial_code == phone_identity.dial_code,
                OtpChallengeRow.phone_number == phone_identity.phone_number,
                OtpChallengeRow.flow_type == flow_type.value,
            )
            .order_by(desc(OtpChallengeRow.created_at))
        )
        return row.to_domain() if row is not None else None

    async def consume_if_available(self, *, challenge_id: UUID, now: datetime) -> bool:
        result = await self._session.execute(
            update(OtpChallengeRow)
            .where(
                OtpChallengeRow.id == str(challenge_id),
                OtpChallengeRow.consumed_at.is_(None),
                OtpChallengeRow.expires_at > now,
                OtpChallengeRow.attempts_left > 0,
            )
            .values(consumed_at=now)
        )
        return result.rowcount == 1

    async def decrement_attempt_if_available(
        self, *, challenge_id: UUID, expected_attempts_left: int
    ) -> bool:
        result = await self._session.execute(
            update(OtpChallengeRow)
            .where(
                OtpChallengeRow.id == str(challenge_id),
                OtpChallengeRow.consumed_at.is_(None),
                OtpChallengeRow.attempts_left == expected_attempts_left,
                OtpChallengeRow.attempts_left > 0,
            )
            .values(attempts_left=OtpChallengeRow.attempts_left - 1)
        )
        return result.rowcount == 1

    async def save(self, challenge: OtpChallenge) -> None:
        row = await self._session.scalar(
            select(OtpChallengeRow).where(OtpChallengeRow.id == str(challenge.id))
        )
        if row is None:
            self._session.add(OtpChallengeRow.from_domain(challenge))
            return
        row.update_from_domain(challenge)


class SqlAlchemyRefreshSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: RefreshSession) -> None:
        self._session.add(RefreshSessionRow.from_domain(session))

    async def get_by_token_id(self, token_id: str) -> RefreshSession | None:
        row = await self._session.scalar(
            select(RefreshSessionRow).where(RefreshSessionRow.token_id == token_id)
        )
        return row.to_domain() if row is not None else None

    async def rotate(
        self,
        *,
        session_id: UUID,
        now: datetime,
        replacement_token_id: str,
    ) -> bool:
        result = await self._session.execute(
            update(RefreshSessionRow)
            .where(
                RefreshSessionRow.id == str(session_id),
                RefreshSessionRow.revoked_at.is_(None),
                RefreshSessionRow.rotated_at.is_(None),
                RefreshSessionRow.expires_at > now,
            )
            .values(
                rotated_at=now,
                revoked_at=now,
                replacement_token_id=replacement_token_id,
            )
        )
        return result.rowcount == 1

    async def revoke(self, *, session_id: UUID, now: datetime) -> bool:
        result = await self._session.execute(
            update(RefreshSessionRow)
            .where(
                RefreshSessionRow.id == str(session_id),
                RefreshSessionRow.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return result.rowcount == 1

    async def revoke_all_for_account(self, *, account_id: UUID, now: datetime) -> int:
        result = await self._session.execute(
            update(RefreshSessionRow)
            .where(
                RefreshSessionRow.account_id == str(account_id),
                RefreshSessionRow.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return result.rowcount

    async def delete_expired_revoked(self, *, before: datetime) -> int:
        result = await self._session.execute(
            delete(RefreshSessionRow).where(
                RefreshSessionRow.expires_at < before,
                RefreshSessionRow.revoked_at.is_not(None),
            )
        )
        return result.rowcount


class SqlAlchemyAccountStatusChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, change: AccountStatusChange) -> None:
        self._session.add(AccountStatusChangeRow.from_domain(change))
