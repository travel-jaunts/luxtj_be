from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.payment.domain.transaction import PaymentGatewayTransaction
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_models import (
    PaymentGatewayTransactionRow,
)
from luxtj.utils import timeutils


class SqlAlchemyPaymentGatewayTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: PaymentGatewayTransaction) -> None:
        self._session.add(PaymentGatewayTransactionRow.from_domain(entity))
        # Session factory uses autoflush=False — flush so follow-up reads/initiate see the row.
        await self._session.flush()

    async def get_by_transaction_id(
        self, transaction_id: str
    ) -> PaymentGatewayTransaction | None:
        row = await self._session.scalar(
            select(PaymentGatewayTransactionRow).where(
                PaymentGatewayTransactionRow.transaction_id == transaction_id
            )
        )
        return row.to_domain() if row is not None else None

    async def count_by_app_reference(self, app_reference: str) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(PaymentGatewayTransactionRow)
            .where(PaymentGatewayTransactionRow.app_reference == app_reference)
        )
        return int(result or 0)

    async def list_by_app_reference(
        self, app_reference: str
    ) -> list[PaymentGatewayTransaction]:
        rows = (
            await self._session.scalars(
                select(PaymentGatewayTransactionRow).where(
                    PaymentGatewayTransactionRow.app_reference == app_reference
                )
            )
        ).all()
        return [row.to_domain() for row in rows]

    async def list_accepted_by_app_reference(
        self, app_reference: str
    ) -> list[PaymentGatewayTransaction]:
        rows = (
            await self._session.scalars(
                select(PaymentGatewayTransactionRow).where(
                    PaymentGatewayTransactionRow.app_reference == app_reference,
                    PaymentGatewayTransactionRow.status == "accepted",
                )
            )
        ).all()
        return [row.to_domain() for row in rows]

    async def update_status(
        self,
        transaction_id: str,
        status: str,
        response_params: dict[str, Any] | list | None = None,
    ) -> None:
        values: dict[str, Any] = {
            "status": status.lower(),
            "updated_at": timeutils.datetime_now(),
        }
        if isinstance(response_params, (dict, list)):
            values["response_params"] = response_params
        await self._session.execute(
            update(PaymentGatewayTransactionRow)
            .where(PaymentGatewayTransactionRow.transaction_id == transaction_id)
            .values(**values)
        )

    async def update_pg_reference_id(self, transaction_id: str, pg_reference_id: str) -> None:
        await self._session.execute(
            update(PaymentGatewayTransactionRow)
            .where(PaymentGatewayTransactionRow.transaction_id == transaction_id)
            .values(
                pg_reference_id=pg_reference_id,
                updated_at=timeutils.datetime_now(),
            )
        )

    async def apply_refund(
        self,
        transaction_id: str,
        *,
        status: str,
        refunded_amount: Any,
        refund_remark: str | None,
        refund_mode: str,
        refund_details: dict[str, Any] | None,
        response_params: dict[str, Any] | list | None = None,
    ) -> None:
        now = timeutils.datetime_now()
        values: dict[str, Any] = {
            "status": status.lower(),
            "refunded_amount": refunded_amount,
            "refund_remark": refund_remark,
            "refund_mode": refund_mode,
            "refund_details": refund_details,
            "refunded_at": now,
            "updated_at": now,
        }
        if isinstance(response_params, (dict, list)):
            values["response_params"] = response_params
        await self._session.execute(
            update(PaymentGatewayTransactionRow)
            .where(PaymentGatewayTransactionRow.transaction_id == transaction_id)
            .values(**values)
        )
        await self._session.flush()
