from admin_api.customer.offers.domainmodel import OfferDomainModel, OffersKpiSummaryDomainModel
from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils


class CustomerOffersService:
    def __init__(self) -> None:
        return

    async def get_kpi_summary(self) -> OffersKpiSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return OffersKpiSummaryDomainModel.generate_mock()

    async def get_offers_list(
        self, page: int, page_size: int, iso_currency_str: str
    ) -> tuple[list[OfferDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        offers_list = [OfferDomainModel.generate_mock() for _ in range(num_items)]

        return offers_list, PaginationMeta(total=num_items, page=page, size=page_size)
