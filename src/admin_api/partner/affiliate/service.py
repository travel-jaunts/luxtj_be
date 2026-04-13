from datetime import date

from admin_api.partner.affiliate.domainmodel import (
    AffiliatePartnerBizKpiSummaryDomainModel,
    AffiliatePartnerDetailsDomainModel,
    AffiliatePartnerDomainModel,
)
from admin_api.partner.affiliate.dto import UpdateAffiliatePartnerDetailsDTO
from common.service.metadata import PaginationMeta
from luxtj.domain.enums import PartnerStatusControlActionEnum
from luxtj.utils import mockutils


class AffiliatePartnerService:
    def __init__(self) -> None:
        return

    async def get_biz_kpi_summary(self) -> AffiliatePartnerBizKpiSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return AffiliatePartnerBizKpiSummaryDomainModel.generate_mock()

    async def get_list(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[AffiliatePartnerDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)
        partner_list = [AffiliatePartnerDomainModel.generate_mock() for _ in range(num_items)]
        return partner_list, PaginationMeta(
            total=num_items,
            page=page,
            size=page_size,
        )

    async def get_details(self, partner_id: str) -> AffiliatePartnerDetailsDomainModel:
        """
        Fetch full details for a specific affiliate partner.
        """
        # TODO: Implement actual fetching logic here
        return AffiliatePartnerDetailsDomainModel.generate_mock()

    async def update_details(
        self,
        partner_id: str,
        update_dto: UpdateAffiliatePartnerDetailsDTO,
    ) -> AffiliatePartnerDetailsDomainModel:
        """
        Update details for a specific affiliate partner.
        """
        # TODO: Implement actual update logic here
        return AffiliatePartnerDetailsDomainModel.generate_mock()

    async def update_status(
        self,
        partner_id: str,
        action: PartnerStatusControlActionEnum,
    ) -> None:
        """
        Apply a status control action to an affiliate partner.
        """
        # TODO: Implement actual status update logic here
        pass
