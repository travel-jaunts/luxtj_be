from typing import Annotated

from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.contexts.payment.application.service import PaymentGatewayService
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPaymentGatewayTransactionRepository,
)
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
)


def build_payment_transaction_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> SqlAlchemyPaymentGatewayTransactionRepository:
    return SqlAlchemyPaymentGatewayTransactionRepository(session)


def build_payment_gateway_service(
    repository: Annotated[
        SqlAlchemyPaymentGatewayTransactionRepository,
        Depends(build_payment_transaction_repository),
    ],
    http_client: Annotated[AsyncClient, Depends(http_client_handle)],
) -> PaymentGatewayService:
    return PaymentGatewayService(
        repository=repository,
        http_client=http_client,
        registry=get_integration_registry(),
    )
