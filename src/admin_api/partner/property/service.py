from admin_api.partner.property.domainmodel import (
    PartnerBizKpiSummaryDomainModel,
    PropertyPartnerDomainModel,
)
from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils


class PartnerService:
    def __init__(self) -> None:
        return

    async def get_biz_kpi_summary(self) -> PartnerBizKpiSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return PartnerBizKpiSummaryDomainModel.generate_mock()

    async def get_list(
        self, page: int, page_size: int
    ) -> tuple[list[PropertyPartnerDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        partner_list = [PropertyPartnerDomainModel.generate_mock() for _ in range(num_items)]
        return partner_list, PaginationMeta(
            total=num_items,
            page=page,
            size=page_size,
        )
