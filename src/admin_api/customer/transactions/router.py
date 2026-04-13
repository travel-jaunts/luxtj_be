from typing import Annotated

from fastapi import APIRouter, Body, Depends

from admin_api.customer.transactions.serializers import (
    PaymentRefundKpiSummarySerializer,
    PaymentsLineItem,
    RefundPaymentBody,
)
from admin_api.customer.transactions.service import CustomerPaymentService
from common.serializerlib import (
    ApiSuccessResponse,
    CurrencyQuery,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)

transactions_router = APIRouter(prefix="/transactions")


@transactions_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[PaymentRefundKpiSummarySerializer],
    status_code=200,
    summary="Get customer KPI summary",
    name="Customer KPI Summary",
)
async def payments_kpi_summary(
    payments_service: Annotated[CustomerPaymentService, Depends(CustomerPaymentService)],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaymentRefundKpiSummarySerializer]:
    """
    Get customer KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await payments_service.get_biz_kpi_summary(iso_currency_str=iso_currency_str)

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
async def list_customer_payments(
    payments_service: Annotated[CustomerPaymentService, Depends(CustomerPaymentService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[PaymentsLineItem]]:
    """
    List payments and refunds for all customers with pagination
    """
    # TODO: access control: restrict this endpoint to admin users only
    payments_list, pagination_meta = await payments_service.get_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
        iso_currency_str=iso_currency_str,
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


@transactions_router.post(
    "/{transaction_id}/details",
    response_model=ApiSuccessResponse[PaymentsLineItem],
    status_code=200,
    summary="Get details of a specific transaction",
    name="Get Transaction Details",
)
async def get_transaction_details(
    transaction_id: str,
    payments_service: Annotated[CustomerPaymentService, Depends(CustomerPaymentService)],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaymentsLineItem]:
    """
    Get details of a specific transaction
    """
    # TODO: access control: restrict this endpoint to admin users only
    transaction_details = await payments_service.get_payment_details(
        payment_id=transaction_id, iso_currency_str=iso_currency_str
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaymentsLineItem.from_domain_model(transaction_details),
    )


@transactions_router.post(
    "/{transaction_id}/refund",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Refund a specific transaction",
    name="Refund Transaction",
)
async def refund_transaction(
    transaction_id: str,
    payments_service: Annotated[CustomerPaymentService, Depends(CustomerPaymentService)],
    refund_body: Annotated[RefundPaymentBody, Body(...)],
) -> ApiSuccessResponse[str]:
    """
    Refund a specific transaction
    """
    # TODO: access control: restrict this endpoint to admin users only
    await payments_service.refund_payment(
        payment_id=transaction_id, amount=refund_body.amount, reason=refund_body.reason
    )

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Transaction {transaction_id} has been refunded with amount {refund_body.amount} for reason: {refund_body.reason}",
    )
