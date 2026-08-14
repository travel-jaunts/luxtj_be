from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.account.domain.account import Account
from luxtj.contexts.account.domain.enums import AccountStatus, AuthFlowType
from luxtj.contexts.account.domain.otp_challenge import OtpChallenge
from luxtj.contexts.account.domain.refresh_session import RefreshSession
from luxtj.contexts.account.domain.status_change import AccountStatusChange
from luxtj.contexts.account.domain.value_objects import PhoneIdentity


class AccountAuthBase(DeclarativeBase):
    pass


class AccountRow(AccountAuthBase):
    __tablename__ = "account_accounts"
    __table_args__ = (
        UniqueConstraint("dial_code", "phone_number", name="uq_account_identity"),
        Index("ix_account_identity", "dial_code", "phone_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dial_code: Mapped[str] = mapped_column(String(8), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccountStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, account: Account) -> AccountRow:
        return cls(
            id=str(account.id),
            dial_code=account.phone_identity.dial_code,
            phone_number=account.phone_identity.phone_number,
            email=account.email,
            status=account.status.value,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    def update_from_domain(self, account: Account) -> None:
        self.email = account.email
        self.status = account.status.value
        self.updated_at = account.updated_at

    def to_domain(self) -> Account:
        return Account(
            id=UUID(self.id),
            phone_identity=PhoneIdentity(self.dial_code, self.phone_number),
            email=self.email,
            status=AccountStatus(self.status),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class OtpChallengeRow(AccountAuthBase):
    __tablename__ = "account_otp_challenges"
    __table_args__ = (
        Index(
            "ix_otp_lookup",
            "dial_code",
            "phone_number",
            "flow_type",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dial_code: Mapped[str] = mapped_column(String(8), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    flow_type: Mapped[str] = mapped_column(String(16), nullable=False)
    otp_hash: Mapped[str] = mapped_column(Text, nullable=False)
    otp_salt: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts_left: Mapped[int] = mapped_column(Integer, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, challenge: OtpChallenge) -> OtpChallengeRow:
        return cls(
            id=str(challenge.id),
            dial_code=challenge.phone_identity.dial_code,
            phone_number=challenge.phone_identity.phone_number,
            flow_type=challenge.flow_type.value,
            otp_hash=challenge.otp_hash,
            otp_salt=challenge.otp_salt,
            expires_at=challenge.expires_at,
            attempts_left=challenge.attempts_left,
            consumed_at=challenge.consumed_at,
            created_at=challenge.created_at,
        )

    def update_from_domain(self, challenge: OtpChallenge) -> None:
        self.attempts_left = challenge.attempts_left
        self.consumed_at = challenge.consumed_at

    def to_domain(self) -> OtpChallenge:
        return OtpChallenge(
            id=UUID(self.id),
            phone_identity=PhoneIdentity(self.dial_code, self.phone_number),
            flow_type=AuthFlowType(self.flow_type),
            otp_hash=self.otp_hash,
            otp_salt=self.otp_salt,
            expires_at=self.expires_at,
            attempts_left=self.attempts_left,
            consumed_at=self.consumed_at,
            created_at=self.created_at,
        )


class RefreshSessionRow(AccountAuthBase):
    __tablename__ = "account_refresh_sessions"
    __table_args__ = (
        UniqueConstraint("token_id", name="uq_account_refresh_session_token_id"),
        Index("ix_account_refresh_session_account", "account_id"),
        Index("ix_account_refresh_session_expiry", "expires_at"),
        Index("ix_account_refresh_session_revoked", "revoked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replacement_token_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    @classmethod
    def from_domain(cls, session: RefreshSession) -> RefreshSessionRow:
        return cls(
            id=str(session.id),
            account_id=str(session.account_id),
            token_id=session.token_id,
            token_hash=session.token_hash,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            rotated_at=session.rotated_at,
            revoked_at=session.revoked_at,
            replacement_token_id=session.replacement_token_id,
        )

    def to_domain(self) -> RefreshSession:
        return RefreshSession(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            token_id=self.token_id,
            token_hash=self.token_hash,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
            rotated_at=self.rotated_at,
            revoked_at=self.revoked_at,
            replacement_token_id=self.replacement_token_id,
        )


class AccountStatusChangeRow(AccountAuthBase):
    __tablename__ = "account_status_changes"
    __table_args__ = (Index("ix_account_status_changes_account", "account_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, change: AccountStatusChange) -> AccountStatusChangeRow:
        return cls(
            id=str(change.id),
            account_id=str(change.account_id),
            actor_id=change.actor_id,
            reason=change.reason,
            from_status=change.from_status.value,
            to_status=change.to_status.value,
            changed_at=change.changed_at,
        )
