from datetime import date

from admin_api.partner.approvals.domainmodel import (
    ApprovalContentDetailsDomainModel,
    ApprovalKycDetailsDomainModel,
    ApprovalLineItemDomainModel,
    ApprovalSummaryDomainModel,
    LifetimeApprovalSummaryDomainModel,
)
from common.service.metadata import PaginationMeta
from luxtj.domain.enums import ApprovalControlActionEnum
from luxtj.utils import mockutils


class PartnerApprovalsService:
    def __init__(self) -> None:
        return

    async def get_summary(self) -> ApprovalSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return ApprovalSummaryDomainModel.generate_mock()

    async def get_lifetime_summary(self) -> LifetimeApprovalSummaryDomainModel:
        # TODO: Implement actual fetching logic here
        return LifetimeApprovalSummaryDomainModel.generate_mock()

    async def get_list(
        self,
        page: int,
        page_size: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[ApprovalLineItemDomainModel], PaginationMeta]:
        # TODO: Implement actual fetching logic here
        num_items = mockutils.random.randint(1, 10)
        items = [ApprovalLineItemDomainModel.generate_mock() for _ in range(num_items)]
        return items, PaginationMeta(total=num_items, page=page, size=page_size)

    async def view(self, approval_id: str) -> ApprovalLineItemDomainModel:
        # TODO: Implement actual fetching logic here
        mock_item = ApprovalLineItemDomainModel.generate_mock()
        mock_item.approval_id = approval_id
        return mock_item

    async def update_status(
        self,
        approval_id: str,
        action: ApprovalControlActionEnum,
    ) -> None:
        # TODO: Implement actual status update logic here
        pass

    async def get_kyc_details(self, approval_id: str) -> ApprovalKycDetailsDomainModel:
        # TODO: Implement actual fetching logic here
        return ApprovalKycDetailsDomainModel.generate_mock()

    async def get_content_details(self, approval_id: str) -> ApprovalContentDetailsDomainModel:
        # TODO: Implement actual fetching logic here
        return ApprovalContentDetailsDomainModel.generate_mock()
