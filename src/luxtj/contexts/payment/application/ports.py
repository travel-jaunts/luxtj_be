from typing import Any, Protocol

from luxtj.contexts.payment.domain.transaction import PaymentGatewayTransaction


class PaymentGatewayTransactionRepository(Protocol):
    async def add(self, entity: PaymentGatewayTransaction) -> None: ...

    async def get_by_transaction_id(
        self, transaction_id: str
    ) -> PaymentGatewayTransaction | None: ...

    async def count_by_app_reference(self, app_reference: str) -> int: ...

    async def list_by_app_reference(
        self, app_reference: str
    ) -> list[PaymentGatewayTransaction]: ...

    async def list_accepted_by_app_reference(
        self, app_reference: str
    ) -> list[PaymentGatewayTransaction]: ...

    async def update_status(
        self,
        transaction_id: str,
        status: str,
        response_params: dict[str, Any] | list | None = None,
    ) -> None: ...

    async def update_pg_reference_id(
        self, transaction_id: str, pg_reference_id: str
    ) -> None: ...
