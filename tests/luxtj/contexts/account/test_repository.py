from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_models import (
    AccountAuthBase,
    AccountRow,
)
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyOtpChallengeRepository,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(AccountAuthBase.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as value:
        yield value

    await engine.dispose()


async def test_repository_roundtrip_for_account_and_challenge(session) -> None:
    account_repo = SqlAlchemyAccountRepository(session)
    otp_repo = SqlAlchemyOtpChallengeRepository(session)

    now = datetime.now(tz=UTC)
    account = Account.create(phone_identity=PhoneIdentity("+91", "1112223333"), now=now)
    await account_repo.add(account)

    challenge = OtpChallenge.issue(
        phone_identity=PhoneIdentity("+91", "1112223333"),
        flow_type=AuthFlowType.LOGIN,
        otp_hash="hash",
        otp_salt="salt",
        now=now,
        ttl_seconds=60,
        max_attempts=3,
    )
    await otp_repo.add(challenge)
    await session.commit()

    fetched_account = await account_repo.get_by_phone_identity(PhoneIdentity("+91", "1112223333"))
    assert fetched_account is not None

    fetched_challenge = await otp_repo.find_latest_for_flow(
        phone_identity=PhoneIdentity("+91", "1112223333"),
        flow_type=AuthFlowType.LOGIN,
    )
    assert fetched_challenge is not None
    assert fetched_challenge.otp_hash == "hash"


async def test_unique_constraint_on_phone_identity(session) -> None:
    now = datetime.now(tz=UTC)
    account_1 = Account.create(phone_identity=PhoneIdentity("+1", "555000"), now=now)
    account_2 = Account.create(phone_identity=PhoneIdentity("+1", "555000"), now=now)

    session.add(AccountRow.from_domain(account_1))
    await session.commit()

    session.add(AccountRow.from_domain(account_2))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_repository_email_backfill_update(session) -> None:
    account_repo = SqlAlchemyAccountRepository(session)

    now = datetime.now(tz=UTC)
    account = Account.create(phone_identity=PhoneIdentity("+44", "778899"), now=now)
    await account_repo.add(account)
    await session.commit()

    account.email = "updated@example.com"
    account.updated_at = now
    await account_repo.save(account)
    await session.commit()

    result = await session.scalar(
        select(AccountRow).where(
            AccountRow.dial_code == "+44",
            AccountRow.phone_number == "778899",
        )
    )
    assert result is not None
    assert result.email == "updated@example.com"
