from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, Field

from admin_api.reports.sales.domainmodel import (
    SalesDimensionOptionDomainModel,
    SalesDimensionTypeEnum,
    SalesPeriodTypeEnum,
    SalesReportDomainModel,
    SalesReportRowDomainModel,
    SalesReportTotalsDomainModel,
    SalesReportTypeEnum,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class SalesReportQuery(ApiSerializerBaseModel):
    report_type: SalesReportTypeEnum = Field(
        SalesReportTypeEnum.DAILY,
        alias="reportType",
        description="Sales report to return for the dashboard tab",
    )
    from_date: date | None = Field(None, description="Start date for the report range")
    to_date: date | None = Field(None, description="End date for the report range")


class SalesDimensionSearchQuery(ApiSerializerBaseModel):
    dimension_type: SalesDimensionTypeEnum = Field(
        ...,
        alias="dimensionType",
        description="Dimension lookup type. Supported values are destination and property.",
    )
    search_query: str | None = Field(
        None,
        alias="q",
        description="User-entered text used to search destinations or properties",
    )


class SalesDimensionOption(ApiSerializerBaseModel):
    dimension_type: SalesDimensionTypeEnum
    dimension_id: str
    dimension_name: str

    @classmethod
    def from_domain_model(
        cls, domain_model: SalesDimensionOptionDomainModel
    ) -> SalesDimensionOption:
        return cls(
            dimension_type=domain_model.dimension_type,
            dimension_id=domain_model.dimension_id,
            dimension_name=domain_model.dimension_name,
        )


class SalesReportTotals(ApiSerializerBaseModel):
    sales: AmountSerializer
    booking_count: int
    units_sold: int
    average_order_value: AmountSerializer

    @classmethod
    def from_domain_model(cls, domain_model: SalesReportTotalsDomainModel) -> SalesReportTotals:
        return cls(
            sales=AmountSerializer(
                amount=domain_model.sales_amount,
                currency=domain_model.currency,
            ),
            booking_count=domain_model.booking_count,
            units_sold=domain_model.units_sold,
            average_order_value=AmountSerializer(
                amount=domain_model.average_order_value,
                currency=domain_model.currency,
            ),
        )


class SalesReportRow(ApiSerializerBaseModel):
    timestamp: date
    period_type: SalesPeriodTypeEnum
    dimension_type: SalesDimensionTypeEnum
    dimension_id: str
    dimension_name: str
    sales: AmountSerializer
    booking_count: int
    units_sold: int
    average_order_value: AmountSerializer

    @classmethod
    def from_domain_model(cls, domain_model: SalesReportRowDomainModel) -> SalesReportRow:
        return cls(
            timestamp=domain_model.timestamp,
            period_type=domain_model.period_type,
            dimension_type=domain_model.dimension_type,
            dimension_id=domain_model.dimension_id,
            dimension_name=domain_model.dimension_name,
            sales=AmountSerializer(
                amount=domain_model.sales_amount,
                currency=domain_model.currency,
            ),
            booking_count=domain_model.booking_count,
            units_sold=domain_model.units_sold,
            average_order_value=AmountSerializer(
                amount=domain_model.average_order_value,
                currency=domain_model.currency,
            ),
        )


class SalesReport(ApiSerializerBaseModel):
    report_type: SalesReportTypeEnum
    title: str
    generated_at: AwareDatetime
    currency: str
    totals: SalesReportTotals
    rows: list[SalesReportRow]

    @classmethod
    def from_domain_model(cls, domain_model: SalesReportDomainModel) -> SalesReport:
        return cls(
            report_type=domain_model.report_type,
            title=domain_model.title,
            generated_at=domain_model.generated_at,
            currency=domain_model.currency,
            totals=SalesReportTotals.from_domain_model(domain_model.totals),
            rows=[SalesReportRow.from_domain_model(row) for row in domain_model.rows],
        )
