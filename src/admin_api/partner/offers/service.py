from datetime import date

from admin_api.partner.offers.domainmodel import (
    OfferPricingActivityLineItemDomainModel,
    OfferPricingCommissionLineItemDomainModel,
    OfferPricingPropertyLineItemDomainModel,
    OfferPricingSeasonalLineItemDomainModel,
    OfferPricingSummaryDomainModel,
    PartnerOfferLineItemDomainModel,
)
from admin_api.partner.offers.dto import (
    CreatePartnerOfferDTO,
    UpdateActivityPricingDTO,
    UpdateCommissionDTO,
    UpdatePartnerOfferDTO,
    UpdatePropertyPricingDTO,
    UpdateSeasonalPricingDTO,
)
from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils


class PartnerOffersService:
    def __init__(self) -> None:
        return

    async def get_pricing_summary(self) -> OfferPricingSummaryDomainModel:
        return OfferPricingSummaryDomainModel.generate_mock()

    async def get_property_items(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[OfferPricingPropertyLineItemDomainModel], PaginationMeta]:
        num_items = mockutils.random.randint(1, 10)
        return [
            OfferPricingPropertyLineItemDomainModel.generate_mock() for _ in range(num_items)
        ], PaginationMeta(total=num_items, page=page, size=page_size)

    async def update_property_item_pricing(
        self,
        property_id: str,
        update_dto: UpdatePropertyPricingDTO,
    ) -> OfferPricingPropertyLineItemDomainModel:
        return OfferPricingPropertyLineItemDomainModel.generate_mock()

    async def get_activity_items(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[OfferPricingActivityLineItemDomainModel], PaginationMeta]:
        num_items = mockutils.random.randint(1, 10)
        return [
            OfferPricingActivityLineItemDomainModel.generate_mock() for _ in range(num_items)
        ], PaginationMeta(total=num_items, page=page, size=page_size)

    async def update_activity_item_pricing(
        self,
        activity_id: str,
        update_dto: UpdateActivityPricingDTO,
    ) -> OfferPricingActivityLineItemDomainModel:
        return OfferPricingActivityLineItemDomainModel.generate_mock()

    async def get_commission_items(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[OfferPricingCommissionLineItemDomainModel], PaginationMeta]:
        num_items = mockutils.random.randint(1, 10)
        return [
            OfferPricingCommissionLineItemDomainModel.generate_mock() for _ in range(num_items)
        ], PaginationMeta(total=num_items, page=page, size=page_size)

    async def update_commission_item(
        self,
        commission_id: str,
        update_dto: UpdateCommissionDTO,
    ) -> OfferPricingCommissionLineItemDomainModel:
        return OfferPricingCommissionLineItemDomainModel.generate_mock()

    async def get_offer_items(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[PartnerOfferLineItemDomainModel], PaginationMeta]:
        num_items = mockutils.random.randint(1, 10)
        return [PartnerOfferLineItemDomainModel.generate_mock() for _ in range(num_items)], PaginationMeta(
            total=num_items,
            page=page,
            size=page_size,
        )

    async def create_offer_item(self, create_dto: CreatePartnerOfferDTO) -> PartnerOfferLineItemDomainModel:
        return PartnerOfferLineItemDomainModel.generate_mock()

    async def update_offer_item(
        self,
        offer_id: str,
        update_dto: UpdatePartnerOfferDTO,
    ) -> PartnerOfferLineItemDomainModel:
        return PartnerOfferLineItemDomainModel.generate_mock()

    async def get_seasonal_pricing_items(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[OfferPricingSeasonalLineItemDomainModel], PaginationMeta]:
        num_items = mockutils.random.randint(1, 10)
        return [
            OfferPricingSeasonalLineItemDomainModel.generate_mock() for _ in range(num_items)
        ], PaginationMeta(total=num_items, page=page, size=page_size)

    async def update_seasonal_pricing_item(
        self,
        seasonal_price_id: str,
        update_dto: UpdateSeasonalPricingDTO,
    ) -> OfferPricingSeasonalLineItemDomainModel:
        return OfferPricingSeasonalLineItemDomainModel.generate_mock()
