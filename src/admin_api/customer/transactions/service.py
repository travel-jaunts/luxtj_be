from datetime import date

from admin_api.customer.transactions.domainmodel import (
    CustomerPaymentDomainModel,
    PaymentRefundKpiSummaryDomainModel,
)
from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils


class CustomerPaymentService:
    def __init__(self):
        pass

    async def get_list(
        self, page: int, page_size: int, *, from_date: date | None = None, to_date: date | None = None, iso_currency_str: str
    ) -> tuple[list[CustomerPaymentDomainModel], PaginationMeta]:
        """
        Fetch a paginated list of customer payments from the database.
        - page: The page number to fetch (starting from 1)
        - page_size: The number of items per page
        Returns a tuple of (list of customer payments, pagination metadata)
        """
        # TODO: Implement actual fetching logic here

        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        payments_list = [
            CustomerPaymentDomainModel.generate_mock(mock_currency=iso_currency_str)
            for _ in range(num_items)
        ]
        return payments_list, PaginationMeta(total=num_items, page=page, size=page_size)

    async def get_biz_kpi_summary(
        self, *, iso_currency_str: str
    ) -> PaymentRefundKpiSummaryDomainModel:
        """
        Fetch payment-related business KPI summary data.
        Returns a PaymentRefundKpiSummaryDomainModel instance containing the KPI data.
        """
        # TODO: Implement actual fetching logic here
        return PaymentRefundKpiSummaryDomainModel.generate_mock(mock_currency=iso_currency_str)

    async def get_payment_details(self, payment_id: str, *, iso_currency_str: str) -> CustomerPaymentDomainModel:
        """
        Fetch detailed information about a specific payment by its ID.
        - payment_id: The unique identifier of the payment to fetch details for
        Returns a CustomerPaymentDomainModel instance containing the payment details.
        """
        # TODO: Implement actual fetching logic here
        return CustomerPaymentDomainModel.generate_mock(mock_currency=iso_currency_str)

    async def refund_payment(self, payment_id: str, amount: float, reason: str) -> None:
        """
        Process a refund for a specific payment.
        - payment_id: The unique identifier of the payment to refund
        - amount: The amount to refund
        - reason: The reason for the refund
        Returns a CustomerPaymentDomainModel instance representing the refund transaction.
        """
        # TODO: Implement actual refund logic here
        pass
