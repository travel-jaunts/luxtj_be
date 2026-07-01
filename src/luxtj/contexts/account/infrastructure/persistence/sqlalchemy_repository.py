from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_models import (
    AccountRow,
    OtpChallengeRow,
)


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: Account) -> None:
        self._session.add(AccountRow.from_domain(account))

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

    async def save(self, challenge: OtpChallenge) -> None:
        row = await self._session.scalar(
            select(OtpChallengeRow).where(OtpChallengeRow.id == str(challenge.id))
        )
        if row is None:
            self._session.add(OtpChallengeRow.from_domain(challenge))
            return
        row.update_from_domain(challenge)
