from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.entities import ActiveCurrency, CurrencyMeta
from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_models import (
    ActiveCurrencyRow,
    CurrencyCatalogRow,
)
from luxtj.utils import timeutils


class SqlAlchemyActiveCurrencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_codes(self) -> list[str]:
        result = await self._session.execute(
            select(ActiveCurrencyRow.currency_code).order_by(ActiveCurrencyRow.currency_code)
        )
        return [str(code).upper().strip() for code in result.scalars().all() if code]

    async def is_active(self, currency_code: str) -> bool:
        code = currency_code.upper().strip()
        result = await self._session.execute(
            select(ActiveCurrencyRow.id).where(ActiveCurrencyRow.currency_code == code).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_code(self, currency_code: str) -> ActiveCurrency | None:
        code = currency_code.upper().strip()
        result = await self._session.execute(
            select(ActiveCurrencyRow).where(ActiveCurrencyRow.currency_code == code)
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def activate(self, currency_code: str) -> ActiveCurrency:
        code = currency_code.upper().strip()
        existing = await self.get_by_code(code)
        if existing is not None:
            return existing
        now = timeutils.datetime_now()
        entity = ActiveCurrency(id=uuid4(), currency_code=code, created_at=now, updated_at=now)
        self._session.add(
            ActiveCurrencyRow(
                id=str(entity.id),
                currency_code=entity.currency_code,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )
        await self._session.flush()
        return entity

    async def deactivate(self, currency_code: str) -> bool:
        code = currency_code.upper().strip()
        result = await self._session.execute(
            delete(ActiveCurrencyRow).where(ActiveCurrencyRow.currency_code == code)
        )
        await self._session.flush()
        return (result.rowcount or 0) > 0

    async def list_currency_metadata(self) -> list[CurrencyMeta]:
        result = await self._session.execute(
            select(CurrencyCatalogRow).order_by(CurrencyCatalogRow.code)
        )
        return [row.to_currency_meta() for row in result.scalars().all()]

    async def ensure_currency_catalog(self, catalog: list[CurrencyMeta]) -> None:
        existing = await self._session.execute(select(CurrencyCatalogRow.code))
        have = {str(c).upper() for c in existing.scalars().all() if c}
        now = timeutils.datetime_now()
        for item in catalog:
            code = item.code.upper().strip()
            if not code or code in have:
                continue
            self._session.add(
                CurrencyCatalogRow(
                    id=str(uuid4()),
                    code=code,
                    name=item.currency_name,
                    symbol=item.currency_symbol or "",
                    created_at=now,
                    updated_at=now,
                )
            )
            have.add(code)
        await self._session.flush()
