from datetime import date

from admin_api.partner.agent.domainmodel import (
    AgentPartnerBizKpiSummaryDomainModel,
    AgentPartnerDetailsDomainModel,
    AgentPartnerDomainModel,
)
from admin_api.partner.agent.dto import UpdateAgentPartnerDetailsDTO
from common.service.metadata import PaginationMeta
from luxtj.domain.enums import PartnerStatusControlActionEnum
from luxtj.utils import mockutils


class AgentPartnerService:
    def __init__(self) -> None:
        return

    async def get_biz_kpi_summary(self) -> AgentPartnerBizKpiSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return AgentPartnerBizKpiSummaryDomainModel.generate_mock()

    async def get_list(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[AgentPartnerDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)
        partner_list = [AgentPartnerDomainModel.generate_mock() for _ in range(num_items)]
        return partner_list, PaginationMeta(
            total=num_items,
            page=page,
            size=page_size,
        )

    async def get_details(self, partner_id: str) -> AgentPartnerDetailsDomainModel:
        """
        Fetch full details for a specific agent partner.
        """
        # TODO: Implement actual fetching logic here
        return AgentPartnerDetailsDomainModel.generate_mock()

    async def update_details(
        self,
        partner_id: str,
        update_dto: UpdateAgentPartnerDetailsDTO,
    ) -> AgentPartnerDetailsDomainModel:
        """
        Update details for a specific agent partner.
        """
        # TODO: Implement actual update logic here
        return AgentPartnerDetailsDomainModel.generate_mock()

    async def update_status(
        self,
        partner_id: str,
        action: PartnerStatusControlActionEnum,
    ) -> None:
        """
        Apply a status control action to an agent partner.
        """
        # TODO: Implement actual status update logic here
        pass
