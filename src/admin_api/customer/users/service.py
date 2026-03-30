from typing import List, Tuple
from datetime import datetime, timezone

from common.service.metadata import PaginationMeta
from admin_api.customer.users.domainmodel import (
    CustomerDomainModel,
    CustomerTierEnum,
    CustomerBizKpiSummaryDomainModel,
)


class CustomerUserService:
    def __init__(self):
        pass

    def get_list(
        self, page: int, page_size: int, *, iso_currency_str: str
    ) -> Tuple[List[CustomerDomainModel], PaginationMeta]:
        """
        Fetch a paginated list of customers from the database.
        - page: The page number to fetch (starting from 1)
        - page_size: The number of items per page
        Returns a tuple of (list of customers, pagination metadata)
        """
        # TODO: Implement actual fetching logic here
        customer_list = [
            CustomerDomainModel(
                user_id="123",
                user_amount_currency=iso_currency_str,
                user_first_name="John",
                user_last_name="Doe",
                user_email="john.doe@example.com",
                user_phone_number="+1234567890",
                user_base_location="New York",
                user_registration_date=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                user_last_booking_date=datetime(2023, 6, 1, 15, 30, 0, tzinfo=timezone.utc),
                user_total_spend=1000.0,
                user_booking_count=5,
                user_average_order_value=200.0,
                user_cancellation_count=1,
                user_is_active=True,
                user_tier=CustomerTierEnum.NOVUS,
                user_status="Active",
            )
        ]
        return customer_list, PaginationMeta(total=1, page=page, size=page_size)

    def get_biz_kpi_summary(self, *, iso_currency_str: str) -> CustomerBizKpiSummaryDomainModel:
        """
        Fetch business KPI summary for customers.
        - iso_currency_str: The ISO currency code to use for monetary values in the summary
        Returns a CustomerBizKpiSummaryDomainModel containing the KPI data.
        """
        # TODO: Implement actual fetching logic here
        return CustomerBizKpiSummaryDomainModel(
            amount_currency=iso_currency_str,
            total_revenue=0.0,
            average_order_value=0.0,
            total_customers=0,
            active_customers=0,
            repeat_rate=0.0,
            cancellation_rate=0.0,
            customers_by_tier={tier: 0 for tier in CustomerTierEnum},
        )
