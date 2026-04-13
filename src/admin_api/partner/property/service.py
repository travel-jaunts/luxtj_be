from datetime import date

from admin_api.partner.property.domainmodel import (
    PartnerBizKpiSummaryDomainModel,
    PropertyPartnerDetailsDomainModel,
    PropertyPartnerDomainModel,
)
from admin_api.partner.property.dto import UpdatePropertyPartnerDetailsDTO
from common.service.metadata import PaginationMeta
from luxtj.domain.enums import PartnerStatusControlActionEnum
from luxtj.utils import mockutils


class PartnerService:
    def __init__(self) -> None:
        return

    async def get_biz_kpi_summary(self) -> PartnerBizKpiSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return PartnerBizKpiSummaryDomainModel.generate_mock()

    async def get_list(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[PropertyPartnerDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        partner_list = [PropertyPartnerDomainModel.generate_mock() for _ in range(num_items)]
        return partner_list, PaginationMeta(
            total=num_items,
            page=page,
            size=page_size,
        )

    async def get_details(self, partner_id: str) -> PropertyPartnerDetailsDomainModel:
        """
        Fetch full details for a specific property partner.
        """
        # TODO: Implement actual fetching logic here
        return PropertyPartnerDetailsDomainModel.generate_mock()

    async def update_details(
        self,
        partner_id: str,
        update_dto: UpdatePropertyPartnerDetailsDTO,
    ) -> PropertyPartnerDetailsDomainModel:
        """
        Update details for a specific property partner.
        """
        # TODO: Implement actual update logic here
        return PropertyPartnerDetailsDomainModel.generate_mock()

    async def update_status(
        self,
        partner_id: str,
        action: PartnerStatusControlActionEnum,
    ) -> None:
        """
        Apply a status control action to a property partner.
        """
        # TODO: Implement actual status update logic here
        pass
