from datetime import date, datetime, timezone

from admin_api.customer.support.domainmodel import SupportKpiSummary, SupportTicketDomainModel
from common.service.metadata import PaginationMeta
from luxtj.domain.enums import SupportTicketStatusEnum
from luxtj.utils import mockutils


class CustomerSupportService:
    def __init__(self):
        pass

    async def get_support_tickets(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        search_query: str | None = None,
    ) -> tuple[list[SupportTicketDomainModel], PaginationMeta]:
        """
        Fetch a paginated list of support tickets with optional filtering.
        - page: The page number to fetch (starting from 1)
        - page_size: The number of items per page
        - from_date: Optional start date filter (inclusive)
        - to_date: Optional end date filter (inclusive)
        - search_query: Optional text search filter
        Returns a tuple of (list of tickets, pagination metadata)
        """
        # TODO: Implement actual fetching logic here

        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        ticket_list = [SupportTicketDomainModel.generate_mock() for _ in range(num_items)]
        return ticket_list, PaginationMeta(total=num_items, page=page, size=page_size)

    async def assign_agent(
        self,
        ticket_id: str,
        agent_id: str,
    ) -> SupportTicketDomainModel:
        """
        Assign an agent to a support ticket.
        - ticket_id: The ID of the support ticket
        - agent_id: The ID of the agent to assign
        Returns the updated support ticket.
        """
        # TODO: Implement actual assign agent logic here
        return SupportTicketDomainModel.generate_mock()

    async def resolve_ticket(
        self,
        ticket_id: str,
        resolution_note: str | None = None,
    ) -> SupportTicketDomainModel:
        """
        Mark a support ticket as resolved.
        - ticket_id: The ID of the support ticket
        - resolution_note: Optional note describing the resolution
        Returns the updated support ticket.
        """
        # TODO: Implement actual resolve ticket logic here
        mock = SupportTicketDomainModel.generate_mock()
        mock.status = SupportTicketStatusEnum.CLOSED
        mock.resolution_date = datetime.now(tz=timezone.utc)
        return mock

    async def get_kpi_summary(self) -> SupportKpiSummary:
        # TODO: Implement actual fetching logic here
        return SupportKpiSummary.generate_mock()
