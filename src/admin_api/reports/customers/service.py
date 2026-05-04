from __future__ import annotations

from datetime import UTC, date, datetime

from admin_api.customer.users.domainmodel import CustomerDomainModel
from admin_api.reports.customers.domainmodel import (
    CustomerOverviewDomainModel,
    CustomerReportIdentityDomainModel,
    CustomerSatisfactionReportDomainModel,
    CustomerValueReportDomainModel,
    mock_customer_overview,
    mock_customer_value_row,
)
from luxtj.utils import mockutils

CUSTOMER_REPORT_OPTIONS = [
    CustomerReportIdentityDomainModel.from_customer_model(CustomerDomainModel.generate_mock())
    for _ in range(16)
]


class CustomerReportService:
    async def get_overview(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        iso_currency_str: str,
    ) -> CustomerOverviewDomainModel:
        return mock_customer_overview(
            currency=iso_currency_str,
            from_date=from_date,
            to_date=to_date,
        )

    async def get_customer_value(
        self,
        *,
        customer_ids: list[str] | None = None,
        iso_currency_str: str,
    ) -> CustomerValueReportDomainModel:
        customers = self._filter_customers_by_id(customer_ids)
        rows = [
            mock_customer_value_row(customer=customer, currency=iso_currency_str)
            for customer in customers
        ]
        return CustomerValueReportDomainModel.from_rows(
            currency=iso_currency_str,
            rows=rows,
        )

    async def get_satisfaction(
        self,
        *,
        customer_id: str,
    ) -> CustomerSatisfactionReportDomainModel:
        customer = self._customer_by_id(customer_id)
        support_ticket_count = mockutils.random.randint(0, 18)
        return CustomerSatisfactionReportDomainModel(
            title="Customer Satisfaction",
            generated_at=datetime.now(tz=UTC),
            customer=customer,
            average_rating=round(mockutils.random.uniform(2.5, 5.0), 2),
            rating_count=mockutils.random.randint(0, 80),
            review_count=mockutils.random.randint(0, 50),
            complaint_count=mockutils.random.randint(0, 12),
            support_ticket_count=support_ticket_count,
            open_support_ticket_count=mockutils.random.randint(0, support_ticket_count),
            average_support_resolution_hours=round(mockutils.random.uniform(1.0, 72.0), 2),
        )

    def _filter_customers_by_id(
        self,
        customer_ids: list[str] | None,
    ) -> list[CustomerReportIdentityDomainModel]:
        if not customer_ids:
            return CUSTOMER_REPORT_OPTIONS

        normalized_ids = {customer_id.lower() for customer_id in customer_ids}
        return [
            customer
            for customer in CUSTOMER_REPORT_OPTIONS
            if customer.customer_id.lower() in normalized_ids
        ]

    def _customer_by_id(self, customer_id: str) -> CustomerReportIdentityDomainModel:
        for customer in CUSTOMER_REPORT_OPTIONS:
            if customer.customer_id.lower() == customer_id.lower():
                return customer

        customer_model = CustomerDomainModel.generate_mock()
        return CustomerReportIdentityDomainModel(
            customer_id=customer_id,
            customer_name=(
                f"{customer_model.user_first_name} {customer_model.user_last_name}".strip()
            ),
            email=customer_model.user_email,
            phone_number=customer_model.user_phone_number,
        )
