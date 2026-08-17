from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyActiveCurrencyRepository,
)
from luxtj.contexts.integration.application.use_cases import IntegrationRegistryService
from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyIntegrationRepository,
)
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle


def build_integration_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> SqlAlchemyIntegrationRepository:
    return SqlAlchemyIntegrationRepository(session)


def build_integration_registry_service(
    repository: Annotated[SqlAlchemyIntegrationRepository, Depends(build_integration_repository)],
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> IntegrationRegistryService:
    return IntegrationRegistryService(
        repository=repository,
        currency_repository=SqlAlchemyActiveCurrencyRepository(session),
        cache=get_integration_registry(),
    )
