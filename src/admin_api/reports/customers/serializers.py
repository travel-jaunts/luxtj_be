from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, Field

from admin_api.reports.customers.domainmodel import (
    CustomerOverviewDomainModel,
    CustomerReportIdentityDomainModel,
    CustomerSatisfactionReportDomainModel,
    CustomerSpendCategoryEnum,
    CustomerValueReportDomainModel,
    CustomerValueRowDomainModel,
    CustomerValueTotalsDomainModel,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class CustomerOverviewQuery(ApiSerializerBaseModel):
    from_date: date | None = Field(None, description="Start date for overview metrics")
    to_date: date | None = Field(None, description="End date for overview metrics")


class CustomerReportIdentity(ApiSerializerBaseModel):
    customer_id: str
    customer_name: str
    email: str
    phone_number: str

    @classmethod
    def from_domain_model(
        cls, domain_model: CustomerReportIdentityDomainModel
    ) -> CustomerReportIdentity:
        return cls(
            customer_id=domain_model.customer_id,
            customer_name=domain_model.customer_name,
            email=domain_model.email,
            phone_number=domain_model.phone_number,
        )


class CustomerOverview(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    currency: str
    from_date: date | None
    to_date: date | None
    total_customers: int
    new_customers: int
    active_customers: int
    average_booking_value: AmountSerializer

    @classmethod
    def from_domain_model(cls, domain_model: CustomerOverviewDomainModel) -> CustomerOverview:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            from_date=domain_model.from_date,
            to_date=domain_model.to_date,
            total_customers=domain_model.total_customers,
            new_customers=domain_model.new_customers,
            active_customers=domain_model.active_customers,
            average_booking_value=AmountSerializer(
                amount=domain_model.average_booking_value,
                currency=domain_model.currency,
            ),
        )


class CustomerValueTotals(ApiSerializerBaseModel):
    customer_count: int
    customer_lifetime_value: AmountSerializer
    revenue: AmountSerializer
    revenue_per_customer: AmountSerializer
    high_value_customer_count: int
    customers_by_spend_category: dict[CustomerSpendCategoryEnum, int]

    @classmethod
    def from_domain_model(cls, domain_model: CustomerValueTotalsDomainModel) -> CustomerValueTotals:
        return cls(
            customer_count=domain_model.customer_count,
            customer_lifetime_value=AmountSerializer(
                amount=domain_model.lifetime_value,
                currency=domain_model.currency,
            ),
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.currency,
            ),
            revenue_per_customer=AmountSerializer(
                amount=domain_model.revenue_per_customer,
                currency=domain_model.currency,
            ),
            high_value_customer_count=domain_model.high_value_customer_count,
            customers_by_spend_category=domain_model.customers_by_spend_category,
        )


class CustomerValueRow(ApiSerializerBaseModel):
    customer: CustomerReportIdentity
    customer_lifetime_value: AmountSerializer
    revenue_per_customer: AmountSerializer
    booking_count: int
    average_booking_value: AmountSerializer
    is_high_value_customer: bool
    spend_category: CustomerSpendCategoryEnum

    @classmethod
    def from_domain_model(cls, domain_model: CustomerValueRowDomainModel) -> CustomerValueRow:
        return cls(
            customer=CustomerReportIdentity.from_domain_model(domain_model.customer),
            customer_lifetime_value=AmountSerializer(
                amount=domain_model.lifetime_value,
                currency=domain_model.currency,
            ),
            revenue_per_customer=AmountSerializer(
                amount=domain_model.revenue_per_customer,
                currency=domain_model.currency,
            ),
            booking_count=domain_model.booking_count,
            average_booking_value=AmountSerializer(
                amount=domain_model.average_booking_value,
                currency=domain_model.currency,
            ),
            is_high_value_customer=domain_model.is_high_value_customer,
            spend_category=domain_model.spend_category,
        )


class CustomerValueReport(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    currency: str
    totals: CustomerValueTotals
    rows: list[CustomerValueRow]

    @classmethod
    def from_domain_model(cls, domain_model: CustomerValueReportDomainModel) -> CustomerValueReport:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            totals=CustomerValueTotals.from_domain_model(domain_model.totals),
            rows=[CustomerValueRow.from_domain_model(row) for row in domain_model.rows],
        )


class CustomerSatisfactionReport(ApiSerializerBaseModel):
    title: str
    generated_at: AwareDatetime
    customer: CustomerReportIdentity
    average_rating: float
    rating_count: int
    review_count: int
    complaint_count: int
    support_ticket_count: int
    open_support_ticket_count: int
    average_support_resolution_hours: float

    @classmethod
    def from_domain_model(
        cls, domain_model: CustomerSatisfactionReportDomainModel
    ) -> CustomerSatisfactionReport:
        return cls(
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            customer=CustomerReportIdentity.from_domain_model(domain_model.customer),
            average_rating=domain_model.average_rating,
            rating_count=domain_model.rating_count,
            review_count=domain_model.review_count,
            complaint_count=domain_model.complaint_count,
            support_ticket_count=domain_model.support_ticket_count,
            open_support_ticket_count=domain_model.open_support_ticket_count,
            average_support_resolution_hours=domain_model.average_support_resolution_hours,
        )
