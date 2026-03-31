from typing import List, Tuple

from common.service.metadata import PaginationMeta

from admin_api.customer.support.domainmodel import SupportKpiSummary, SupportTicketDomainModel
from luxtj.utils import mockutils


class CustomerSupportService:
    def __init__(self):
        pass

    def get_support_tickets(
        self,
        page: int,
        page_size: int,
    ) -> Tuple[List[SupportTicketDomainModel], PaginationMeta]:
        """
        Fetch a paginated list of customers from the database.
        - page: The page number to fetch (starting from 1)
        - page_size: The number of items per page
        Returns a tuple of (list of customers, pagination metadata)
        """
        # TODO: Implement actual fetching logic here

        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        customer_list = [SupportTicketDomainModel.generate_mock() for _ in range(num_items)]
        return customer_list, PaginationMeta(total=num_items, page=page, size=page_size)

    def get_kpi_summary(self) -> SupportKpiSummary:
        # TODO: Implement actual fetching logic here
        return SupportKpiSummary.generate_mock()
