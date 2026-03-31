from typing import List, Tuple

from common.service.metadata import PaginationMeta

from admin_api.customer.payments.domainmodel import (
    CustomerPaymentDomainModel,
    PaymentRefundKpiSummaryDomainModel,
)

from luxtj.utils import mockutils


class CustomerPaymentService:
    def __init__(self):
        pass

    def get_list(
        self, page: int, page_size: int, *, iso_currency_str: str
    ) -> Tuple[List[CustomerPaymentDomainModel], PaginationMeta]:
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

    def get_biz_kpi_summary(self, *, iso_currency_str: str) -> PaymentRefundKpiSummaryDomainModel:
        """
        Fetch payment-related business KPI summary data.
        Returns a PaymentRefundKpiSummaryDomainModel instance containing the KPI data.
        """
        # TODO: Implement actual fetching logic here
        return PaymentRefundKpiSummaryDomainModel.generate_mock(mock_currency=iso_currency_str)
