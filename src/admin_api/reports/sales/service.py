from __future__ import annotations

from datetime import date

from admin_api.reports.sales.domainmodel import (
    SalesDimensionOptionDomainModel,
    SalesDimensionTypeEnum,
    SalesPeriodTypeEnum,
    SalesReportDomainModel,
    SalesReportTypeEnum,
    date_range_days,
    mock_sales_report_row,
    month_range,
)

DESTINATION_OPTIONS = [
    ("DXB", "Dubai"),
    ("MLE", "Maldives"),
    ("BKK", "Bangkok"),
    ("SIN", "Singapore"),
    ("LHR", "London"),
    ("NYC", "New York"),
]

PROPERTY_OPTIONS = [
    ("PROP-001", "Luxury Apartment"),
    ("PROP-002", "Cozy Villa"),
    ("PROP-003", "Spacious Cottage"),
    ("PROP-004", "Modern Studio"),
    ("PROP-005", "Beachfront Bungalow"),
]


class SalesReportService:
    async def get_report(
        self,
        *,
        report_type: SalesReportTypeEnum,
        from_date: date | None = None,
        to_date: date | None = None,
        destination_ids: list[str] | None = None,
        property_ids: list[str] | None = None,
        iso_currency_str: str,
    ) -> SalesReportDomainModel:
        if report_type == SalesReportTypeEnum.MONTHLY:
            return self._monthly_sales(
                from_date=from_date,
                to_date=to_date,
                iso_currency_str=iso_currency_str,
            )
        if report_type == SalesReportTypeEnum.DESTINATION:
            return self._destination_sales(
                destination_ids=destination_ids,
                iso_currency_str=iso_currency_str,
            )
        if report_type == SalesReportTypeEnum.PROPERTY:
            return self._property_sales(
                property_ids=property_ids,
                iso_currency_str=iso_currency_str,
            )
        return self._daily_sales(
            from_date=from_date,
            to_date=to_date,
            iso_currency_str=iso_currency_str,
        )

    async def search_dimensions(
        self,
        *,
        dimension_type: SalesDimensionTypeEnum,
        search_query: str | None = None,
    ) -> list[SalesDimensionOptionDomainModel]:
        if dimension_type == SalesDimensionTypeEnum.DESTINATION:
            options = DESTINATION_OPTIONS
        elif dimension_type == SalesDimensionTypeEnum.PROPERTY:
            options = PROPERTY_OPTIONS
        else:
            return []

        normalized_query = (search_query or "").strip().lower()
        if normalized_query:
            options = [
                (option_id, option_name)
                for option_id, option_name in options
                if normalized_query in option_id.lower() or normalized_query in option_name.lower()
            ]

        return [
            SalesDimensionOptionDomainModel(
                dimension_type=dimension_type,
                dimension_id=option_id,
                dimension_name=option_name,
            )
            for option_id, option_name in options
        ]

    def _daily_sales(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        iso_currency_str: str,
    ) -> SalesReportDomainModel:
        rows = [
            mock_sales_report_row(
                timestamp=report_date,
                period_type=SalesPeriodTypeEnum.DAILY,
                dimension_type=SalesDimensionTypeEnum.OVERALL,
                dimension_id="ALL",
                dimension_name="All Sales",
                currency=iso_currency_str,
            )
            for report_date in date_range_days(
                from_date=from_date,
                to_date=to_date,
                fallback_days=14,
            )
        ]
        return SalesReportDomainModel.from_rows(
            report_type=SalesReportTypeEnum.DAILY,
            title="Daily Sales",
            currency=iso_currency_str,
            rows=rows,
        )

    def _monthly_sales(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        iso_currency_str: str,
    ) -> SalesReportDomainModel:
        rows = [
            mock_sales_report_row(
                timestamp=report_month,
                period_type=SalesPeriodTypeEnum.MONTHLY,
                dimension_type=SalesDimensionTypeEnum.OVERALL,
                dimension_id="ALL",
                dimension_name="All Sales",
                currency=iso_currency_str,
            )
            for report_month in month_range(
                from_date=from_date,
                to_date=to_date,
                fallback_months=12,
            )
        ]
        return SalesReportDomainModel.from_rows(
            report_type=SalesReportTypeEnum.MONTHLY,
            title="Monthly Sales",
            currency=iso_currency_str,
            rows=rows,
        )

    def _destination_sales(
        self,
        *,
        destination_ids: list[str] | None,
        iso_currency_str: str,
    ) -> SalesReportDomainModel:
        destinations = self._filter_options_by_id(DESTINATION_OPTIONS, destination_ids)
        rows = [
            mock_sales_report_row(
                timestamp=date.today(),
                period_type=SalesPeriodTypeEnum.RANGE,
                dimension_type=SalesDimensionTypeEnum.DESTINATION,
                dimension_id=destination_id,
                dimension_name=destination_name,
                currency=iso_currency_str,
            )
            for destination_id, destination_name in destinations
        ]
        return SalesReportDomainModel.from_rows(
            report_type=SalesReportTypeEnum.DESTINATION,
            title="Destination Sales",
            currency=iso_currency_str,
            rows=rows,
        )

    def _property_sales(
        self,
        *,
        property_ids: list[str] | None,
        iso_currency_str: str,
    ) -> SalesReportDomainModel:
        properties = self._filter_options_by_id(PROPERTY_OPTIONS, property_ids)
        rows = [
            mock_sales_report_row(
                timestamp=date.today(),
                period_type=SalesPeriodTypeEnum.RANGE,
                dimension_type=SalesDimensionTypeEnum.PROPERTY,
                dimension_id=property_id,
                dimension_name=property_name,
                currency=iso_currency_str,
            )
            for property_id, property_name in properties
        ]
        return SalesReportDomainModel.from_rows(
            report_type=SalesReportTypeEnum.PROPERTY,
            title="Property Sales",
            currency=iso_currency_str,
            rows=rows,
        )

    def _filter_options_by_id(
        self,
        options: list[tuple[str, str]],
        selected_ids: list[str] | None,
    ) -> list[tuple[str, str]]:
        if not selected_ids:
            return options

        normalized_ids = {selected_id.lower() for selected_id in selected_ids}
        return [
            (option_id, option_name)
            for option_id, option_name in options
            if option_id.lower() in normalized_ids
        ]
