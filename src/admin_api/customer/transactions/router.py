from typing import Annotated

from fastapi import APIRouter, Depends

from common.serializerlib import (
    RequestProcessStatus,
    ApiSuccessResponse,
    PaginationParams,
    PaginatedResult,
    CurrencyQuery,
)
from admin_api.customer.transactions.serializers import (
    PaymentsLineItem,
    PaymentRefundKpiSummarySerializer,
)
from admin_api.customer.transactions.service import CustomerPaymentService


transactions_router = APIRouter(prefix="/transactions")


@transactions_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[PaymentRefundKpiSummarySerializer],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
def payments_kpi_summary(
    payments_service: Annotated[CustomerPaymentService, Depends(CustomerPaymentService)],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaymentRefundKpiSummarySerializer]:
    """
    Get customer KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = payments_service.get_biz_kpi_summary(iso_currency_str=iso_currency_str)

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaymentRefundKpiSummarySerializer.from_domain_model(kpi_summary),
    )


@transactions_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[PaymentsLineItem]],
    status_code=200,
    summary="List payments for all customers with pagination and filtering",
    name="List Customer Payments",
)
def list_customer_payments(
    payments_service: Annotated[CustomerPaymentService, Depends(CustomerPaymentService)],
    query: Annotated[PaginationParams, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[PaymentsLineItem]]:
    """
    List payments and refunds for all customers with pagination
    """
    # TODO: access control: restrict this endpoint to admin users only
    payments_list, pagination_meta = payments_service.get_list(
        page=query.page, page_size=query.size, iso_currency_str=iso_currency_str
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=pagination_meta.total,  # Replace with actual total count from database
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[PaymentsLineItem.from_domain_model(payment) for payment in payments_list],
        ),
    )
