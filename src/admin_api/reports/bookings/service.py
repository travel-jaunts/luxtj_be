from __future__ import annotations

from datetime import date

from admin_api.customer.users.domainmodel import CustomerDomainModel
from admin_api.reports.bookings.domainmodel import (
    BookingReportCustomerOptionDomainModel,
    BookingReportDomainModel,
    BookingReportGroupByEnum,
    BookingReportTypeEnum,
    day_points,
    mock_booking_report_row,
    month_points,
    report_date_range,
)

CUSTOMER_OPTIONS = [
    BookingReportCustomerOptionDomainModel.from_customer_model(CustomerDomainModel.generate_mock())
    for _ in range(12)
]


class BookingReportService:
    async def get_report(
        self,
        *,
        report_type: BookingReportTypeEnum,
        group_by: BookingReportGroupByEnum,
        from_date: date | None = None,
        to_date: date | None = None,
        customer_ids: list[str] | None = None,
        iso_currency_str: str,
    ) -> BookingReportDomainModel:
        resolved_from_date, resolved_to_date = report_date_range(
            from_date=from_date,
            to_date=to_date,
            fallback_days=30,
        )
        customers = self._filter_customers_by_id(customer_ids)

        if group_by == BookingReportGroupByEnum.MONTH:
            rows = self._month_rows(
                from_date=resolved_from_date,
                to_date=resolved_to_date,
                iso_currency_str=iso_currency_str,
            )
        elif group_by == BookingReportGroupByEnum.CUSTOMER:
            rows = self._customer_rows(
                customers=customers,
                iso_currency_str=iso_currency_str,
            )
        else:
            rows = self._day_rows(
                from_date=resolved_from_date,
                to_date=resolved_to_date,
                iso_currency_str=iso_currency_str,
            )

        if report_type == BookingReportTypeEnum.CANCELLATIONS:
            title = f"Cancellations by {group_by.value}"
        else:
            title = f"Booking Overview by {group_by.value}"

        return BookingReportDomainModel.from_rows(
            report_type=report_type,
            group_by=group_by,
            title=title,
            currency=iso_currency_str,
            rows=rows,
        )

    async def search_customers(
        self,
        *,
        search_query: str | None = None,
    ) -> list[BookingReportCustomerOptionDomainModel]:
        normalized_query = (search_query or "").strip().lower()
        if not normalized_query:
            return CUSTOMER_OPTIONS

        return [
            customer
            for customer in CUSTOMER_OPTIONS
            if normalized_query in customer.customer_id.lower()
            or normalized_query in customer.customer_name.lower()
            or normalized_query in customer.email.lower()
            or normalized_query in customer.phone_number.lower()
        ]

    def _day_rows(
        self,
        *,
        from_date: date,
        to_date: date,
        iso_currency_str: str,
    ):
        return [
            mock_booking_report_row(
                group_by=BookingReportGroupByEnum.DAY,
                label=report_date.isoformat(),
                period_start=report_date,
                customer=None,
                currency=iso_currency_str,
            )
            for report_date in day_points(
                from_date=from_date,
                to_date=to_date,
                max_points=14,
            )
        ]

    def _month_rows(
        self,
        *,
        from_date: date,
        to_date: date,
        iso_currency_str: str,
    ):
        return [
            mock_booking_report_row(
                group_by=BookingReportGroupByEnum.MONTH,
                label=report_month.strftime("%Y-%m"),
                period_start=report_month,
                customer=None,
                currency=iso_currency_str,
            )
            for report_month in month_points(from_date=from_date, to_date=to_date)
        ]

    def _customer_rows(
        self,
        *,
        customers: list[BookingReportCustomerOptionDomainModel],
        iso_currency_str: str,
    ):
        return [
            mock_booking_report_row(
                group_by=BookingReportGroupByEnum.CUSTOMER,
                label=customer.customer_name,
                period_start=None,
                customer=customer,
                currency=iso_currency_str,
            )
            for customer in customers
        ]

    def _filter_customers_by_id(
        self,
        customer_ids: list[str] | None,
    ) -> list[BookingReportCustomerOptionDomainModel]:
        if not customer_ids:
            return CUSTOMER_OPTIONS

        normalized_ids = {customer_id.lower() for customer_id in customer_ids}
        return [
            customer
            for customer in CUSTOMER_OPTIONS
            if customer.customer_id.lower() in normalized_ids
        ]
