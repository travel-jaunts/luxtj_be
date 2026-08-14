from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyActiveCurrencyRepository,
)
from luxtj.contexts.integration.application.commands import (
    UpdateBookingApiCommand,
    UpdateModuleStatusCommand,
    UpdateOtherApiCommand,
    UpdatePaymentGatewayCommand,
    UpdateSubModuleStatusCommand,
)
from luxtj.contexts.integration.domain.catalog import (
    MODULES_AND_THEMES,
    OTHER_APIS,
    PAYMENT_GATEWAYS,
    SUB_MODULES_AND_BOOKING_APIS,
    normalize_booking_api_currency,
    normalize_config_key,
)
from luxtj.contexts.integration.domain.entities import (
    BookingApi,
    Module,
    OtherApi,
    PaymentGateway,
    SubModule,
)
from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyIntegrationRepository,
)
from luxtj.contexts.integration.infrastructure.registry_cache import (
    IntegrationRegistryCache,
    get_integration_registry,
)


class IntegrationNotFoundError(Exception):
    pass


class IntegrationValidationError(Exception):
    pass


class IntegrationRegistryService:
    def __init__(
        self,
        *,
        repository: SqlAlchemyIntegrationRepository,
        currency_repository: SqlAlchemyActiveCurrencyRepository | None = None,
        cache: IntegrationRegistryCache | None = None,
    ) -> None:
        self._repo = repository
        self._currency_repo = currency_repository
        self._cache = cache or get_integration_registry()

    async def _assert_currency_in_catalog(self, currency: str) -> None:
        if self._currency_repo is None:
            return
        known = {
            m.code.upper() for m in await self._currency_repo.list_currency_metadata() if m.code
        }
        if currency.upper() not in known:
            raise IntegrationValidationError(
                f"currency '{currency}' is not in the currencies catalog"
            )

    async def sync_catalog(self) -> None:
        """Idempotent seed from Layer A. Never overwrites credentials."""
        for module_name in MODULES_AND_THEMES:
            existing = await self._repo.get_module_by_name(module_name)
            if existing is None:
                await self._repo.add_module(Module.create(name=module_name))
            elif not existing.status:
                existing.set_status(True)
                await self._repo.save_module(existing)

        # Insert parents first, then flush — BookingApiRow has no ORM relationship
        # to SubModuleRow, so SQLAlchemy may otherwise flush booking_apis first.
        for sub_name in SUB_MODULES_AND_BOOKING_APIS:
            sub = await self._repo.get_sub_module_by_name(sub_name)
            if sub is None:
                await self._repo.add_sub_module(SubModule.create(name=sub_name))
        await self._repo.flush()

        for sub_name, apis in SUB_MODULES_AND_BOOKING_APIS.items():
            sub = await self._repo.get_sub_module_by_name(sub_name)
            if sub is None:
                continue
            for code, entry in apis.items():
                existing_api = await self._repo.get_booking_api_by_code(sub.id, code)
                if existing_api is None:
                    await self._repo.add_booking_api(
                        BookingApi.create(sub_module_id=sub.id, code=code, name=entry.name)
                    )

        for code, entry in PAYMENT_GATEWAYS.items():
            if await self._repo.get_payment_gateway_by_code(code) is None:
                await self._repo.add_payment_gateway(
                    PaymentGateway.create(code=code, name=entry.name)
                )

        # Deactivate gateways / booking APIs removed from the catalog.
        for gateway in await self._repo.list_payment_gateways():
            if gateway.code not in PAYMENT_GATEWAYS and gateway.status:
                gateway.update_settings(status=False)
                await self._repo.save_payment_gateway(gateway)

        for api in await self._repo.list_booking_apis():
            parent = await self._repo.get_sub_module(api.sub_module_id)
            catalog = SUB_MODULES_AND_BOOKING_APIS.get(parent.name if parent else "", {})
            if api.code not in catalog and api.status:
                api.update_settings(status=False)
                await self._repo.save_booking_api(api)

        for code, entry in OTHER_APIS.items():
            if await self._repo.get_other_api_by_code(code) is None:
                await self._repo.add_other_api(OtherApi.create(code=code, name=entry.name))

        for other in await self._repo.list_other_apis():
            if other.code not in OTHER_APIS and other.status:
                other.update_settings(status=False)
                await self._repo.save_other_api(other)

        await self.refresh_cache()

    async def refresh_cache(self) -> None:
        modules = await self._repo.list_modules()
        sub_modules = await self._repo.list_sub_modules()
        booking_apis = await self._repo.list_booking_apis()
        payment_gateways = await self._repo.list_payment_gateways()
        other_apis = await self._repo.list_other_apis()
        self._cache.replace(
            modules=modules,
            sub_modules=sub_modules,
            booking_apis=booking_apis,
            payment_gateways=payment_gateways,
            other_apis=other_apis,
        )

    async def list_overview(self) -> dict:
        modules = await self._repo.list_modules()
        sub_modules = await self._repo.list_sub_modules()
        booking_apis = await self._repo.list_booking_apis()
        payment_gateways = await self._repo.list_payment_gateways()
        other_apis = await self._repo.list_other_apis()
        sub_by_id = {s.id: s for s in sub_modules}

        booking_catalog: dict[str, dict] = {}
        for sub_name, apis in SUB_MODULES_AND_BOOKING_APIS.items():
            booking_catalog[sub_name] = {
                code: {
                    "name": entry.name,
                    "configs": list(entry.configs),
                    "config_keys": [normalize_config_key(c) for c in entry.configs],
                    "lib_name": entry.lib_name,
                    "auth_required": entry.auth_required,
                }
                for code, entry in apis.items()
            }

        return {
            "modules": modules,
            "subModules": [
                {
                    "entity": s,
                    "catalogApis": booking_catalog.get(s.name, {}),
                }
                for s in sub_modules
            ],
            "bookingApis": [
                {
                    "entity": api,
                    "subModuleName": sub_by_id[api.sub_module_id].name
                    if api.sub_module_id in sub_by_id
                    else None,
                    "catalog": booking_catalog.get(
                        sub_by_id[api.sub_module_id].name if api.sub_module_id in sub_by_id else "",
                        {},
                    ).get(api.code),
                }
                for api in booking_apis
                if api.sub_module_id in sub_by_id
                and api.code in booking_catalog.get(sub_by_id[api.sub_module_id].name, {})
            ],
            "paymentGateways": [
                {
                    "entity": g,
                    "catalog": {
                        "name": PAYMENT_GATEWAYS[g.code].name,
                        "configs": list(PAYMENT_GATEWAYS[g.code].configs),
                        "config_keys": [
                            normalize_config_key(c) for c in PAYMENT_GATEWAYS[g.code].configs
                        ],
                        "currency": PAYMENT_GATEWAYS[g.code].currency,
                        "lib_name": PAYMENT_GATEWAYS[g.code].lib_name,
                        "refund_api": PAYMENT_GATEWAYS[g.code].refund_api,
                    }
                    if g.code in PAYMENT_GATEWAYS
                    else None,
                }
                for g in payment_gateways
                if g.code in PAYMENT_GATEWAYS
            ],
            "otherApis": [
                {
                    "entity": o,
                    "catalog": {
                        "name": OTHER_APIS[o.code].name,
                        "configs": list(OTHER_APIS[o.code].configs),
                        "config_keys": [
                            normalize_config_key(c) for c in OTHER_APIS[o.code].configs
                        ],
                    }
                    if o.code in OTHER_APIS
                    else None,
                }
                for o in other_apis
                if o.code in OTHER_APIS
            ],
            "currencies": await self._list_currency_options(),
        }

    async def _list_currency_options(self) -> list[dict]:
        if self._currency_repo is None:
            return []
        metadata = await self._currency_repo.list_currency_metadata()
        active = {c.upper() for c in await self._currency_repo.list_active_codes()}
        return [
            {
                "code": m.code.upper(),
                "currency_name": m.currency_name,
                "currency_symbol": m.currency_symbol,
                "active": m.code.upper() in active,
            }
            for m in metadata
            if m.code
        ]

    async def update_module_status(self, command: UpdateModuleStatusCommand) -> Module:
        module = await self._repo.get_module(command.module_id)
        if module is None:
            raise IntegrationNotFoundError("Module not found")
        module.set_status(command.status)
        await self._repo.save_module(module)
        await self.refresh_cache()
        return module

    async def update_sub_module_status(self, command: UpdateSubModuleStatusCommand) -> SubModule:
        sub = await self._repo.get_sub_module(command.sub_module_id)
        if sub is None:
            raise IntegrationNotFoundError("Sub-module not found")
        sub.set_status(command.status)
        await self._repo.save_sub_module(sub)
        await self.refresh_cache()
        return sub

    async def update_booking_api(self, command: UpdateBookingApiCommand) -> BookingApi:
        api = await self._repo.get_booking_api(command.booking_api_id)
        if api is None:
            raise IntegrationNotFoundError("Booking API not found")
        sub = await self._repo.get_sub_module(api.sub_module_id)
        catalog = SUB_MODULES_AND_BOOKING_APIS.get(sub.name if sub else "", {})
        if api.code not in catalog:
            raise IntegrationValidationError(f"Booking API '{api.code}' is no longer supported")
        if command.api_type is not None and command.api_type not in {"test", "live"}:
            raise IntegrationValidationError("api_type must be test or live")

        currency = api.currency
        if command.currency is not None:
            normalized = normalize_booking_api_currency(command.currency)
            if command.currency.strip() and normalized is None:
                raise IntegrationValidationError(
                    "currency must be a 3-letter ISO code (e.g. USD, EUR, INR)"
                )
            currency = normalized

        will_be_active = api.status if command.status is None else command.status
        if will_be_active and not currency:
            raise IntegrationValidationError(
                "currency is required when enabling a booking API "
                "(supplier call currency; amounts are converted to admin currency for FE/DB)"
            )
        if currency:
            await self._assert_currency_in_catalog(currency)

        configs = None
        if command.configs is not None:
            configs = {
                normalize_config_key(k) if " " in k else k: v for k, v in command.configs.items()
            }
        api.update_settings(
            status=command.status,
            api_type=command.api_type,
            configs=configs,
        )
        if command.currency is not None:
            api.currency = currency
        await self._repo.save_booking_api(api)
        await self.refresh_cache()
        return api

    async def update_payment_gateway(self, command: UpdatePaymentGatewayCommand) -> PaymentGateway:
        gateway = await self._repo.get_payment_gateway(command.gateway_id)
        if gateway is None:
            raise IntegrationNotFoundError("Payment gateway not found")
        if gateway.code not in PAYMENT_GATEWAYS:
            raise IntegrationValidationError(
                f"Payment gateway '{gateway.code}' is no longer supported"
            )
        if command.api_type is not None and command.api_type not in {"test", "live"}:
            raise IntegrationValidationError("api_type must be test or live")
        if command.convenience_type is not None and command.convenience_type not in {
            "flat",
            "percentage",
        }:
            raise IntegrationValidationError("convenience_type must be flat or percentage")

        currency = gateway.currency
        if command.currency is not None:
            normalized = normalize_booking_api_currency(command.currency)
            if command.currency.strip() and normalized is None:
                raise IntegrationValidationError(
                    "currency must be a 3-letter ISO code (e.g. USD, EUR, INR)"
                )
            currency = normalized
        will_be_active = gateway.status if command.status is None else command.status
        if will_be_active and not currency:
            raise IntegrationValidationError("currency is required when enabling a payment gateway")
        if currency:
            await self._assert_currency_in_catalog(currency)

        configs = None
        if command.configs is not None:
            configs = {
                normalize_config_key(k) if " " in k else k: v for k, v in command.configs.items()
            }
        gateway.update_settings(
            status=command.status,
            api_type=command.api_type,
            convenience_type=command.convenience_type,
            convenience_value=command.convenience_value,
            configs=configs,
        )
        if command.currency is not None:
            gateway.currency = currency
        await self._repo.save_payment_gateway(gateway)
        await self.refresh_cache()
        return gateway

    async def update_other_api(self, command: UpdateOtherApiCommand) -> OtherApi:
        other = await self._repo.get_other_api(command.other_api_id)
        if other is None:
            raise IntegrationNotFoundError("Other API not found")
        if other.code not in OTHER_APIS:
            raise IntegrationValidationError(f"Other API '{other.code}' is no longer supported")
        configs = None
        if command.configs is not None:
            configs = {
                normalize_config_key(k) if " " in k else k: v for k, v in command.configs.items()
            }
        other.update_settings(status=command.status, configs=configs)
        await self._repo.save_other_api(other)
        await self.refresh_cache()
        return other
