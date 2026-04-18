from typing import Annotated

from fastapi import APIRouter, Depends, Query

from admin_api.partner.transactions.serializers import (
    PartnerPaymentsLineItem,
    PartnerRefundsLineItem,
    PartnerTransactionsSummary,
)
from admin_api.partner.transactions.domainmodel import (
    PartnerPaymentStatusEnum,
    PartnerRefundStatusEnum,
)
from admin_api.partner.transactions.service import PartnerTransactionsService
from common.serializerlib import (
    ApiSuccessResponse,
    CurrencyQuery,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    SearchFilterParams,
)

transactions_partner_router = APIRouter()


@transactions_partner_router.post(
    "/summary",
    response_model=ApiSuccessResponse[PartnerTransactionsSummary],
    status_code=200,
    summary="Get partner transactions summary",
    name="Partner Transactions Summary",
)
async def partner_transactions_summary(
    transactions_service: Annotated[PartnerTransactionsService, Depends(PartnerTransactionsService)],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PartnerTransactionsSummary]:
    # TODO: access control: restrict this endpoint to admin users only
    summary = await transactions_service.get_summary(iso_currency_str=iso_currency_str)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PartnerTransactionsSummary.from_domain_model(summary),
    )


@transactions_partner_router.post(
    "/payments/list",
    response_model=ApiSuccessResponse[PaginatedResult[PartnerPaymentsLineItem]],
    status_code=200,
    summary="Get list of partner payments",
    name="List Partner Payments",
)
async def partner_payments_list(
    transactions_service: Annotated[PartnerTransactionsService, Depends(PartnerTransactionsService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[PartnerPaymentsLineItem]]:
    # TODO: access control: restrict this endpoint to admin users only
    payments_list, pagination_meta = await transactions_service.get_payments_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
        iso_currency_str=iso_currency_str,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[PartnerPaymentsLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[PartnerPaymentsLineItem.from_domain_model(item) for item in payments_list],
        ),
    )


@transactions_partner_router.post(
    "/{payment_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for a partner payment",
    name="Partner Payment Status Update",
)
async def partner_payment_status_control(
    transactions_service: Annotated[PartnerTransactionsService, Depends(PartnerTransactionsService)],
    payment_id: str,
    target_status: Annotated[PartnerPaymentStatusEnum, Query(..., alias="to")],
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await transactions_service.update_payment_status(payment_id=payment_id, target_status=target_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Payment {payment_id} status updated to '{target_status}' successfully",
    )


@transactions_partner_router.post(
    "/refunds/list",
    response_model=ApiSuccessResponse[PaginatedResult[PartnerRefundsLineItem]],
    status_code=200,
    summary="Get list of partner refunds",
    name="List Partner Refunds",
)
async def partner_refunds_list(
    transactions_service: Annotated[PartnerTransactionsService, Depends(PartnerTransactionsService)],
    page_query: Annotated[PaginationParams, Depends()],
    search_filter_query: Annotated[SearchFilterParams, Depends()],
    iso_currency_str: CurrencyQuery = "INR",
) -> ApiSuccessResponse[PaginatedResult[PartnerRefundsLineItem]]:
    # TODO: access control: restrict this endpoint to admin users only
    refunds_list, pagination_meta = await transactions_service.get_refunds_list(
        page=page_query.page,
        page_size=page_query.size,
        from_date=search_filter_query.from_date,
        to_date=search_filter_query.to_date,
        iso_currency_str=iso_currency_str,
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[PartnerRefundsLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[PartnerRefundsLineItem.from_domain_model(item) for item in refunds_list],
        ),
    )


@transactions_partner_router.post(
    "/{refund_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for a partner refund",
    name="Partner Refund Status Update",
)
async def partner_refund_status_control(
    transactions_service: Annotated[PartnerTransactionsService, Depends(PartnerTransactionsService)],
    refund_id: str,
    target_status: Annotated[PartnerRefundStatusEnum, Query(..., alias="to")],
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    await transactions_service.update_refund_status(refund_id=refund_id, target_status=target_status)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=f"Refund {refund_id} status updated to '{target_status}' successfully",
    )
