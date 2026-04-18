from datetime import date

from admin_api.partner.transactions.domainmodel import (
    PartnerPaymentLineItemDomainModel,
    PartnerPaymentStatusEnum,
    PartnerRefundLineItemDomainModel,
    PartnerRefundStatusEnum,
    PartnerTransactionsSummaryDomainModel,
)

from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils


class PartnerTransactionsService:
    def __init__(self) -> None:
        return

    async def get_summary(self, *, iso_currency_str: str) -> PartnerTransactionsSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return PartnerTransactionsSummaryDomainModel.generate_mock(iso_currency_str=iso_currency_str)

    async def get_payments_list(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        iso_currency_str: str,
    ) -> tuple[list[PartnerPaymentLineItemDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)
        items = [
            PartnerPaymentLineItemDomainModel.generate_mock(iso_currency_str=iso_currency_str)
            for _ in range(num_items)
        ]
        return items, PaginationMeta(total=num_items, page=page, size=page_size)

    async def update_payment_status(
        self, payment_id: str, target_status: PartnerPaymentStatusEnum
    ) -> None:
        # TODO: Implement actual status update logic here
        # This would fetch the payment by ID, validate the transition, and persist the status change
        pass

    async def get_refunds_list(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        iso_currency_str: str,
    ) -> tuple[list[PartnerRefundLineItemDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)
        items = [
            PartnerRefundLineItemDomainModel.generate_mock(iso_currency_str=iso_currency_str)
            for _ in range(num_items)
        ]
        return items, PaginationMeta(total=num_items, page=page, size=page_size)

    async def update_refund_status(
        self, refund_id: str, target_status: PartnerRefundStatusEnum
    ) -> None:
        # TODO: Implement actual status update logic here
        # This would fetch the refund by ID, validate the transition, and persist the status change
        pass
