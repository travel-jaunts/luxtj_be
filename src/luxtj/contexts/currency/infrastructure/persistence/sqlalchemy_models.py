from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.currency.domain.entities import ActiveCurrency, CurrencyMeta


class CurrencyBase(DeclarativeBase):
    pass


class ActiveCurrencyRow(CurrencyBase):
    __tablename__ = "active_currencies"
    __table_args__ = (UniqueConstraint("currency_code", name="uq_active_currencies_currency_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> ActiveCurrency:
        return ActiveCurrency(
            id=UUID(self.id),
            currency_code=self.currency_code,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class CurrencyCatalogRow(CurrencyBase):
    """ISO currency catalog — source of truth for admin Currencies list / activation."""

    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("code", name="uq_currencies_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_currency_meta(self) -> CurrencyMeta:
        return CurrencyMeta(
            code=self.code.upper(),
            currency_name=self.name,
            currency_symbol=self.symbol or "",
        )


class CountryRow(CurrencyBase):
    """Geo country row — may include default currency fields for the country."""

    __tablename__ = "countries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    currency_name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency_symbol: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CityRow(CurrencyBase):
    __tablename__ = "cities"
    __table_args__ = (
        Index("ix_cities_country_id", "country_id"),
        Index("ix_cities_country_id_name", "country_id", "name"),
        Index("ix_cities_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
