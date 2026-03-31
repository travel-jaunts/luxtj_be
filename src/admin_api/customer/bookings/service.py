from admin_api.customer.bookings.domainmodel import (
    BookingBizKpiSummaryDomainModel,
    CustomerBookingDomainModel,
)
from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils


class CustomerBookingService:
    def __init__(self):
        pass

    def get_list(
        self, page: int, page_size: int, *, iso_currency_str: str
    ) -> tuple[list[CustomerBookingDomainModel], PaginationMeta]:
        """
        Fetch a paginated list of customer bookings from the database.
        - page: The page number to fetch (starting from 1)
        - page_size: The number of items per page
        Returns a tuple of (list of customer bookings, pagination metadata)
        """
        # TODO: Implement actual fetching logic here

        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        customer_bookings_list = [
            CustomerBookingDomainModel.generate_mock(mock_currency=iso_currency_str)
            for _ in range(num_items)
        ]
        return customer_bookings_list, PaginationMeta(total=num_items, page=page, size=page_size)

    def get_biz_kpi_summary(self, *, iso_currency_str: str) -> BookingBizKpiSummaryDomainModel:
        """
        Fetch booking-related business KPI summary data.
        Returns a BookingBizKpiSummaryDomainModel instance containing the KPI data.
        """
        # TODO: Implement actual fetching logic here
        return BookingBizKpiSummaryDomainModel.generate_mock(mock_currency=iso_currency_str)
