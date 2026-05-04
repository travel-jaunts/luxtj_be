from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, Field

from admin_api.reports.bookings.domainmodel import (
    BookingReportCustomerOptionDomainModel,
    BookingReportDomainModel,
    BookingReportGroupByEnum,
    BookingReportRowDomainModel,
    BookingReportTotalsDomainModel,
    BookingReportTypeEnum,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class BookingReportQuery(ApiSerializerBaseModel):
    report_type: BookingReportTypeEnum = Field(
        BookingReportTypeEnum.OVERVIEW,
        alias="reportType",
        description="Bookings report to return for the dashboard tab",
    )
    group_by: BookingReportGroupByEnum = Field(
        BookingReportGroupByEnum.DAY,
        alias="groupBy",
        description="Report grouping. Supported values are day, month, and customer.",
    )
    from_date: date | None = Field(None, description="Start date for the report range")
    to_date: date | None = Field(None, description="End date for the report range")


class BookingCustomerSearchQuery(ApiSerializerBaseModel):
    search_query: str | None = Field(
        None,
        alias="q",
        description="User-entered text used to search customers",
    )


class BookingReportCustomerOption(ApiSerializerBaseModel):
    customer_id: str
    customer_name: str
    email: str
    phone_number: str

    @classmethod
    def from_domain_model(
        cls, domain_model: BookingReportCustomerOptionDomainModel
    ) -> BookingReportCustomerOption:
        return cls(
            customer_id=domain_model.customer_id,
            customer_name=domain_model.customer_name,
            email=domain_model.email,
            phone_number=domain_model.phone_number,
        )


class BookingReportTotals(ApiSerializerBaseModel):
    booking_count: int
    cancellation_count: int
    gross_booking_value: AmountSerializer
    cancelled_value: AmountSerializer
    net_booking_value: AmountSerializer
    average_booking_value: AmountSerializer
    cancellation_rate: float

    @classmethod
    def from_domain_model(cls, domain_model: BookingReportTotalsDomainModel) -> BookingReportTotals:
        return cls(
            booking_count=domain_model.booking_count,
            cancellation_count=domain_model.cancellation_count,
            gross_booking_value=AmountSerializer(
                amount=domain_model.gross_booking_amount,
                currency=domain_model.currency,
            ),
            cancelled_value=AmountSerializer(
                amount=domain_model.cancelled_amount,
                currency=domain_model.currency,
            ),
            net_booking_value=AmountSerializer(
                amount=domain_model.net_booking_amount,
                currency=domain_model.currency,
            ),
            average_booking_value=AmountSerializer(
                amount=domain_model.average_booking_value,
                currency=domain_model.currency,
            ),
            cancellation_rate=domain_model.cancellation_rate,
        )


class BookingReportRow(ApiSerializerBaseModel):
    group_by: BookingReportGroupByEnum
    label: str
    period_start: date | None
    customer: BookingReportCustomerOption | None
    booking_count: int
    cancellation_count: int
    gross_booking_value: AmountSerializer
    cancelled_value: AmountSerializer
    net_booking_value: AmountSerializer
    average_booking_value: AmountSerializer
    cancellation_rate: float

    @classmethod
    def from_domain_model(cls, domain_model: BookingReportRowDomainModel) -> BookingReportRow:
        return cls(
            group_by=domain_model.group_by,
            label=domain_model.label,
            period_start=domain_model.period_start,
            customer=BookingReportCustomerOption.from_domain_model(domain_model.customer)
            if domain_model.customer
            else None,
            booking_count=domain_model.booking_count,
            cancellation_count=domain_model.cancellation_count,
            gross_booking_value=AmountSerializer(
                amount=domain_model.gross_booking_amount,
                currency=domain_model.currency,
            ),
            cancelled_value=AmountSerializer(
                amount=domain_model.cancelled_amount,
                currency=domain_model.currency,
            ),
            net_booking_value=AmountSerializer(
                amount=domain_model.net_booking_amount,
                currency=domain_model.currency,
            ),
            average_booking_value=AmountSerializer(
                amount=domain_model.average_booking_value,
                currency=domain_model.currency,
            ),
            cancellation_rate=domain_model.cancellation_rate,
        )


class BookingReport(ApiSerializerBaseModel):
    report_type: BookingReportTypeEnum
    group_by: BookingReportGroupByEnum
    title: str
    generated_at: AwareDatetime
    currency: str
    totals: BookingReportTotals
    rows: list[BookingReportRow]

    @classmethod
    def from_domain_model(cls, domain_model: BookingReportDomainModel) -> BookingReport:
        return cls(
            report_type=domain_model.report_type,
            group_by=domain_model.group_by,
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            totals=BookingReportTotals.from_domain_model(domain_model.totals),
            rows=[BookingReportRow.from_domain_model(row) for row in domain_model.rows],
        )
