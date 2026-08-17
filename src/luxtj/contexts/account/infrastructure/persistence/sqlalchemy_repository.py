from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.account.application.ports import PiiCipher
from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.album import Album
from luxtj.contexts.account.domain.enums import AuthFlowType
from luxtj.contexts.account.domain.frequent_traveller import FrequentTraveller
from luxtj.contexts.account.domain.gallery_enums import AlbumKind, AlbumVisibility
from luxtj.contexts.account.domain.gallery_image import GalleryImage
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.profile import AccountProfile
from luxtj.contexts.account.domain.refresh_session import RefreshSession
from luxtj.contexts.account.domain.status_change import AccountStatusChange
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_models import (
    AccountAlbumRow,
    AccountGalleryImageRow,
    AccountProfileRow,
    AccountRow,
    AccountStatusChangeRow,
    FrequentTravellerRow,
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


class SqlAlchemyAccountProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, account_id: UUID) -> AccountProfile | None:
        row = await self._session.scalar(
            select(AccountProfileRow).where(AccountProfileRow.account_id == str(account_id))
        )
        return row.to_domain() if row is not None else None

    async def save(self, profile: AccountProfile) -> None:
        row = await self._session.scalar(
            select(AccountProfileRow).where(AccountProfileRow.account_id == str(profile.account_id))
        )
        if row is None:
            self._session.add(AccountProfileRow.from_domain(profile))
            return
        row.update_from_domain(profile)


class SqlAlchemyFrequentTravellerRepository:
    def __init__(self, session: AsyncSession, cipher: PiiCipher) -> None:
        self._session = session
        self._cipher = cipher

    def _encrypted(self, traveller: FrequentTraveller) -> str | None:
        if not traveller.passport_number:
            return None
        return self._cipher.encrypt(traveller.passport_number)

    def _to_domain(self, row: FrequentTravellerRow) -> FrequentTraveller:
        passport_number = (
            self._cipher.decrypt(row.passport_number_encrypted)
            if row.passport_number_encrypted
            else None
        )
        return row.to_domain(passport_number=passport_number)

    async def add(self, traveller: FrequentTraveller) -> None:
        self._session.add(
            FrequentTravellerRow.from_domain(
                traveller, passport_encrypted=self._encrypted(traveller)
            )
        )

    async def get(self, *, account_id: UUID, traveller_id: UUID) -> FrequentTraveller | None:
        row = await self._session.scalar(
            select(FrequentTravellerRow).where(
                FrequentTravellerRow.id == str(traveller_id),
                FrequentTravellerRow.account_id == str(account_id),
            )
        )
        return self._to_domain(row) if row is not None else None

    async def list_for_account(self, account_id: UUID) -> list[FrequentTraveller]:
        rows = await self._session.scalars(
            select(FrequentTravellerRow)
            .where(FrequentTravellerRow.account_id == str(account_id))
            .order_by(FrequentTravellerRow.created_at)
        )
        return [self._to_domain(row) for row in rows]

    async def save(self, traveller: FrequentTraveller) -> None:
        row = await self._session.scalar(
            select(FrequentTravellerRow).where(
                FrequentTravellerRow.id == str(traveller.id),
                FrequentTravellerRow.account_id == str(traveller.account_id),
            )
        )
        if row is None:
            return
        row.update_from_domain(traveller, passport_encrypted=self._encrypted(traveller))

    async def remove(self, *, account_id: UUID, traveller_id: UUID) -> bool:
        result = await self._session.execute(
            delete(FrequentTravellerRow).where(
                FrequentTravellerRow.id == str(traveller_id),
                FrequentTravellerRow.account_id == str(account_id),
            )
        )
        return bool(result.rowcount)


class SqlAlchemyAlbumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, album: Album) -> None:
        self._session.add(AccountAlbumRow.from_domain(album))

    async def get(self, *, account_id: UUID, album_id: UUID) -> Album | None:
        row = await self._session.scalar(
            select(AccountAlbumRow).where(
                AccountAlbumRow.id == str(album_id),
                AccountAlbumRow.account_id == str(account_id),
                AccountAlbumRow.deleted_at.is_(None),
            )
        )
        return row.to_domain() if row is not None else None

    async def get_system(self, *, account_id: UUID, kind: AlbumKind) -> Album | None:
        row = await self._session.scalar(
            select(AccountAlbumRow).where(
                AccountAlbumRow.account_id == str(account_id),
                AccountAlbumRow.kind == kind.value,
                AccountAlbumRow.deleted_at.is_(None),
            )
        )
        return row.to_domain() if row is not None else None

    async def list_for_account(self, account_id: UUID) -> list[Album]:
        rows = await self._session.scalars(
            select(AccountAlbumRow)
            .where(
                AccountAlbumRow.account_id == str(account_id),
                AccountAlbumRow.deleted_at.is_(None),
            )
            .order_by(AccountAlbumRow.created_at)
        )
        return [row.to_domain() for row in rows]

    async def list_public_for_account(self, account_id: UUID) -> list[Album]:
        rows = await self._session.scalars(
            select(AccountAlbumRow)
            .where(
                AccountAlbumRow.account_id == str(account_id),
                AccountAlbumRow.visibility == AlbumVisibility.PUBLIC.value,
                AccountAlbumRow.deleted_at.is_(None),
            )
            .order_by(AccountAlbumRow.created_at)
        )
        return [row.to_domain() for row in rows]

    async def save(self, album: Album) -> None:
        row = await self._session.scalar(
            select(AccountAlbumRow).where(
                AccountAlbumRow.id == str(album.id),
                AccountAlbumRow.account_id == str(album.account_id),
            )
        )
        if row is None:
            return
        row.update_from_domain(album)

    async def clear_cover_image(self, *, account_id: UUID, image_id: UUID) -> None:
        await self._session.execute(
            update(AccountAlbumRow)
            .where(
                AccountAlbumRow.account_id == str(account_id),
                AccountAlbumRow.cover_image_id == str(image_id),
            )
            .values(cover_image_id=None)
        )


class SqlAlchemyGalleryImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, image: GalleryImage) -> None:
        self._session.add(AccountGalleryImageRow.from_domain(image))

    async def get(self, *, account_id: UUID, image_id: UUID) -> GalleryImage | None:
        row = await self._session.scalar(
            select(AccountGalleryImageRow).where(
                AccountGalleryImageRow.id == str(image_id),
                AccountGalleryImageRow.account_id == str(account_id),
                AccountGalleryImageRow.deleted_at.is_(None),
            )
        )
        return row.to_domain() if row is not None else None

    async def list_for_album(self, *, album_id: UUID) -> list[GalleryImage]:
        rows = await self._session.scalars(
            select(AccountGalleryImageRow)
            .where(
                AccountGalleryImageRow.album_id == str(album_id),
                AccountGalleryImageRow.deleted_at.is_(None),
            )
            .order_by(AccountGalleryImageRow.sort_order, AccountGalleryImageRow.created_at)
        )
        return [row.to_domain() for row in rows]

    async def count_for_album(self, *, album_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(AccountGalleryImageRow)
            .where(
                AccountGalleryImageRow.album_id == str(album_id),
                AccountGalleryImageRow.deleted_at.is_(None),
            )
        )
        return int(total or 0)

    async def save(self, image: GalleryImage) -> None:
        row = await self._session.scalar(
            select(AccountGalleryImageRow).where(
                AccountGalleryImageRow.id == str(image.id),
                AccountGalleryImageRow.account_id == str(image.account_id),
            )
        )
        if row is None:
            return
        row.update_from_domain(image)

    async def soft_delete_for_album(self, *, album_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(AccountGalleryImageRow)
            .where(
                AccountGalleryImageRow.album_id == str(album_id),
                AccountGalleryImageRow.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
