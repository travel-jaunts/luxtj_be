from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.application.use_cases import CurrencyActivationService
from luxtj.contexts.currency.infrastructure.active_currencies_cache import (
    get_active_currencies_cache,
)
from luxtj.contexts.currency.infrastructure.currency_conversion import (
    CurrencyConversionService,
    get_currency_conversion,
    set_currency_conversion,
)
from luxtj.contexts.currency.infrastructure.fx_providers import build_default_fx_rate_provider
from luxtj.contexts.currency.infrastructure.fx_rate_cache import get_fx_rate_cache
from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyActiveCurrencyRepository,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle


def build_currency_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> SqlAlchemyActiveCurrencyRepository:
    return SqlAlchemyActiveCurrencyRepository(session)


def build_currency_activation_service(
    repository: Annotated[SqlAlchemyActiveCurrencyRepository, Depends(build_currency_repository)],
) -> CurrencyActivationService:
    return CurrencyActivationService(
        repository=repository,
        cache=get_active_currencies_cache(),
        conversion=get_currency_conversion(),
    )


def init_currency_conversion() -> CurrencyConversionService:
    service = CurrencyConversionService(
        rate_provider=build_default_fx_rate_provider(),
        rate_cache=get_fx_rate_cache(),
        active_cache=get_active_currencies_cache(),
    )
    set_currency_conversion(service)
    return service
