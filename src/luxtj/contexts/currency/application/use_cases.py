from luxtj.bootstrap import config
from luxtj.contexts.currency.application.commands import (
    ActivateCurrencyCommand,
    DeactivateCurrencyCommand,
)
from luxtj.contexts.currency.domain.entities import CurrencyListItem, CurrencyMeta
from luxtj.contexts.currency.domain.symbols import default_currency_symbol
from luxtj.contexts.currency.infrastructure.active_currencies_cache import (
    ActiveCurrenciesCache,
    get_active_currencies_cache,
)
from luxtj.contexts.currency.infrastructure.currency_conversion import (
    CurrencyConversionService,
    get_currency_conversion,
)
from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyActiveCurrencyRepository,
)

# Default rows seeded into the `currencies` catalog table on boot (insert-if-missing).
CURRENCY_CATALOG: list[CurrencyMeta] = [
    CurrencyMeta(code=code, currency_name=name, currency_symbol=symbol)
    for code, name, symbol in (
        ("USD", "US Dollar", "$"),
        ("EUR", "Euro", "€"),
        ("GBP", "British Pound", "£"),
        ("INR", "Indian Rupee", "₹"),
        ("JPY", "Japanese Yen", "¥"),
        ("AED", "UAE Dirham", "د.إ"),
        ("AUD", "Australian Dollar", "A$"),
        ("CAD", "Canadian Dollar", "C$"),
        ("CHF", "Swiss Franc", "CHF"),
        ("SGD", "Singapore Dollar", "S$"),
        ("THB", "Thai Baht", "฿"),
        ("MYR", "Malaysian Ringgit", "RM"),
        ("CNY", "Chinese Yuan", "¥"),
        ("HKD", "Hong Kong Dollar", "HK$"),
        ("NZD", "New Zealand Dollar", "NZ$"),
        ("SAR", "Saudi Riyal", "﷼"),
        ("KRW", "South Korean Won", "₩"),
    )
]


class CurrencyNotFoundError(Exception):
    pass


class CurrencyActivationService:
    def __init__(
        self,
        *,
        repository: SqlAlchemyActiveCurrencyRepository,
        cache: ActiveCurrenciesCache | None = None,
        conversion: CurrencyConversionService | None = None,
    ) -> None:
        self._repo = repository
        self._cache = cache or get_active_currencies_cache()
        self._conversion = conversion or get_currency_conversion()

    async def bootstrap(self) -> None:
        """Seed catalog metadata, ensure admin currency active, rebuild boot cache."""
        await self._repo.ensure_currency_catalog(CURRENCY_CATALOG)
        admin = (config.ADMIN_CURRENCY or "INR").upper().strip()
        if admin:
            await self._repo.activate(admin)
        await self.refresh_cache()

    async def refresh_cache(self) -> None:
        active_codes = {c.upper() for c in await self._repo.list_active_codes()}
        metadata = await self._repo.list_currency_metadata()
        by_code = {m.code.upper(): m for m in metadata}
        items: list[CurrencyMeta] = []
        for code in sorted(active_codes):
            meta = by_code.get(code)
            if meta is not None:
                items.append(meta)
            else:
                items.append(
                    CurrencyMeta(
                        code=code,
                        currency_name=code,
                        currency_symbol=default_currency_symbol(code) or "",
                    )
                )
        self._cache.replace(items)

    async def list_currencies(self) -> list[CurrencyListItem]:
        metadata = await self._repo.list_currency_metadata()
        active = {c.upper() for c in await self._repo.list_active_codes()}
        return [
            CurrencyListItem(
                code=m.code,
                currency_name=m.currency_name,
                currency_symbol=m.currency_symbol or default_currency_symbol(m.code) or "",
                active=m.code.upper() in active,
            )
            for m in metadata
        ]

    async def activate(self, command: ActivateCurrencyCommand) -> CurrencyListItem:
        code = command.currency_code.upper().strip()
        if not code or len(code) != 3:
            raise CurrencyNotFoundError("currency_code must be a 3-letter ISO code")
        known = {m.code.upper() for m in await self._repo.list_currency_metadata()}
        if code not in known:
            raise CurrencyNotFoundError(f"Unknown currency: {code}")
        await self._repo.activate(code)
        await self.refresh_cache()
        items = await self.list_currencies()
        match = next((i for i in items if i.code == code), None)
        if match is None:
            return CurrencyListItem(
                code=code,
                currency_name=code,
                currency_symbol=default_currency_symbol(code) or "",
                active=True,
            )
        return match

    async def deactivate(self, command: DeactivateCurrencyCommand) -> CurrencyListItem:
        code = command.currency_code.upper().strip()
        admin = (config.ADMIN_CURRENCY or "INR").upper().strip()
        if code == admin:
            raise CurrencyNotFoundError("Cannot deactivate the admin base currency")
        await self._repo.deactivate(code)
        await self.refresh_cache()
        items = await self.list_currencies()
        match = next((i for i in items if i.code == code), None)
        if match is None:
            return CurrencyListItem(
                code=code,
                currency_name=code,
                currency_symbol=default_currency_symbol(code) or "",
                active=False,
            )
        return match

    async def get_public_rates(self) -> dict:
        """Mirrors TeenvaStaticDataController::getCurrency."""
        base = self._conversion.get_base_currency()
        active_map = self._cache.get_map()

        def symbol_for(code: str) -> str:
            meta = active_map.get(code.upper())
            if meta and meta.get("currency_symbol"):
                return meta["currency_symbol"]
            return default_currency_symbol(code) or ""

        self._conversion.refresh_all_rates(base)

        conversion_rate: dict[str, dict[str, float | str | None]] = {}
        for code in self._conversion.get_active_currency_codes():
            if code == base:
                continue
            rate = self._conversion.get_cached_rate(base, code)
            conversion_rate[code] = {
                "value": round(rate, 2) if rate is not None else None,
                "symbol": symbol_for(code),
            }

        return {
            "domain_currency": {
                "code": base,
                "symbol": symbol_for(base),
            },
            "conversion_rate": conversion_rate,
        }
