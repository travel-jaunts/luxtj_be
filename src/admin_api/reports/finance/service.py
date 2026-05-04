from __future__ import annotations

from datetime import UTC, date, datetime

from admin_api.reports.finance.domainmodel import (
    FinanceMetricTypeEnum,
    FinanceReportDomainModel,
    default_finance_date_range,
    finance_metric_from_amount,
    finance_trend_dates,
    mock_finance_trend_point,
)


class FinanceReportService:
    async def get_report(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        iso_currency_str: str,
    ) -> FinanceReportDomainModel:
        resolved_from_date, resolved_to_date = default_finance_date_range(
            from_date=from_date,
            to_date=to_date,
            fallback_days=30,
        )
        trend = [
            mock_finance_trend_point(timestamp=trend_date, currency=iso_currency_str)
            for trend_date in finance_trend_dates(
                from_date=resolved_from_date,
                to_date=resolved_to_date,
                max_points=12,
            )
        ]

        revenue_amount = sum(point.revenue_amount for point in trend)
        payments_amount = sum(point.payments_amount for point in trend)
        refunds_amount = sum(point.refunds_amount for point in trend)
        profit_amount = sum(point.profit_amount for point in trend)

        return FinanceReportDomainModel(
            title="Finance Overview",
            generated_at=datetime.now(tz=UTC),
            currency=iso_currency_str,
            from_date=resolved_from_date,
            to_date=resolved_to_date,
            metrics=[
                finance_metric_from_amount(
                    metric_type=FinanceMetricTypeEnum.REVENUE,
                    title="Revenue",
                    amount=revenue_amount,
                    currency=iso_currency_str,
                    transaction_count=self._mock_transaction_count(revenue_amount),
                ),
                finance_metric_from_amount(
                    metric_type=FinanceMetricTypeEnum.PAYMENTS,
                    title="Payments",
                    amount=payments_amount,
                    currency=iso_currency_str,
                    transaction_count=self._mock_transaction_count(payments_amount),
                ),
                finance_metric_from_amount(
                    metric_type=FinanceMetricTypeEnum.REFUNDS,
                    title="Refunds",
                    amount=refunds_amount,
                    currency=iso_currency_str,
                    transaction_count=self._mock_transaction_count(refunds_amount, minimum=1),
                ),
                finance_metric_from_amount(
                    metric_type=FinanceMetricTypeEnum.PROFIT,
                    title="Profit",
                    amount=profit_amount,
                    currency=iso_currency_str,
                    transaction_count=self._mock_transaction_count(revenue_amount),
                ),
            ],
            trend=trend,
        )

    def _mock_transaction_count(self, amount: float, *, minimum: int = 10) -> int:
        return max(minimum, int(amount // 25_000))
