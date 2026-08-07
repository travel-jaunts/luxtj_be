"""Payment gateway HTTP endpoints (popup initiate + callback + JS helper)."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from luxtj.contexts.payment.application.service import PaymentGatewayService
from luxtj.contexts.payment.bootstrap import build_payment_gateway_service
from luxtj.contexts.payment.presentation.http.schemas import (
    PaymentResponseBody,
    PaymentStatusBody,
    PaymentStatusResult,
    PaymentTransactionBody,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

payment_gateway_router = APIRouter(prefix="/payment-gateway", tags=["payment-gateway"])


def _checkout_url(result: dict[str, Any]) -> str | None:
    data = result.get("data") or {}
    payment_data = data.get("payment_data") or {}
    return payment_data.get("checkoutSessionUrl") or (data.get("response") or {}).get("url")


def _response_script(payload: dict[str, Any]) -> HTMLResponse:
    json_response = json.dumps(payload)
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
<script>
window.opener.postMessage({{
    customPaymentGatewayResponse: true,
    response: {json_response}
}}, '*');
window.close();
</script>
<p>You may close this window.</p>
</body>
</html>
"""
    return HTMLResponse(content=html, status_code=200)


def _js_lib(payment_base: str) -> PlainTextResponse:
    payment_url_json = json.dumps(payment_base)
    script = f"""
class CustomPaymentGateway {{
    constructor(config) {{
        if (typeof config !== 'object' || config === null) {{
            throw new Error('Invalid config: Expected an object.');
        }}
        if (!config.appReference) {{
            throw new Error('Invalid config: Missing "appReference".');
        }}
        if (typeof config.handleResponse !== 'function') {{
            throw new Error('Invalid config: "handleResponse" must be a function.');
        }}
        this.appReference = config.appReference;
        this.handleResponse = config.handleResponse;
        this.paymentUrl = {payment_url_json};
        this.popupWindow = null;
    }}

    openPaymentWindow(transactionId) {{
        const url = this.paymentUrl + '/' + (transactionId || this.appReference);
        this.popupWindow = window.open(url, '_blank', 'width=600,height=700,scrollbars=yes,resizable=yes');
        if (!this.popupWindow) {{
            throw new Error('Popup blocked or could not be opened.');
        }}
        window.addEventListener('message', this.handlePostMessage.bind(this), false);
    }}

    handlePostMessage(event) {{
        const data = event.data;
        if (data.customPaymentGatewayResponse === true) {{
            this.handleResponse(data.response);
            if (this.popupWindow) this.popupWindow.close();
        }}
    }}
}}
window.CustomPaymentGateway = CustomPaymentGateway;
"""
    return PlainTextResponse(
        content=script,
        status_code=200,
        media_type="application/javascript; charset=UTF-8",
    )


@payment_gateway_router.post(
    "/payment",
    summary="Initiate payment (redirect URL)",
    name="Payment Gateway Initiate",
    response_model=None,
)
async def payment_post(
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
    body: Annotated[PaymentTransactionBody, Body(...)],
) -> RedirectResponse | JSONResponse:
    record = await service.read_payment_record(body.transaction_id)
    if record is None:
        return JSONResponse(status_code=400, content={"detail": "Invalid Request"})

    result = await service.initiate_payment_for_transaction(body.transaction_id)
    if not result.get("status"):
        return JSONResponse(
            status_code=400,
            content={"detail": result.get("message") or "Payment initiation failed"},
        )

    url = _checkout_url(result)
    if not url:
        return JSONResponse(status_code=400, content={"detail": "Payment URL not available"})
    return RedirectResponse(url=url, status_code=303)


@payment_gateway_router.post(
    "/payment/{transaction_id}",
    summary="Initiate payment by path transaction id",
    name="Payment Gateway Initiate Path",
    response_model=None,
)
async def payment_post_path(
    transaction_id: str,
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
) -> RedirectResponse | JSONResponse:
    return await payment_post(
        service, PaymentTransactionBody(transaction_id=transaction_id)
    )


@payment_gateway_router.get(
    "/payment/{transaction_id}",
    summary="Initiate payment (browser redirect entry)",
    name="Payment Gateway Initiate Get",
    include_in_schema=False,
    response_model=None,
)
async def payment_get(
    transaction_id: str,
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
) -> RedirectResponse | PlainTextResponse:
    record = await service.read_payment_record(transaction_id)
    if record is None:
        return PlainTextResponse("Invalid Request", status_code=400)

    result = await service.initiate_payment_for_transaction(transaction_id)
    if not result.get("status"):
        return PlainTextResponse(
            result.get("message") or "Payment initiation failed", status_code=400
        )

    url = _checkout_url(result)
    if not url:
        return PlainTextResponse("Payment URL not available", status_code=400)
    return RedirectResponse(url=url, status_code=303)


@payment_gateway_router.post(
    "/payment_response",
    summary="Payment callback verify + postMessage HTML",
    name="Payment Gateway Response",
)
async def payment_response_post(
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
    body: Annotated[PaymentResponseBody, Body(...)],
) -> HTMLResponse:
    response: dict[str, Any] = {
        "status": False,
        "message": "Invalid Request",
        "paid_amount": 0,
    }
    record = await service.read_payment_record(body.transaction_id)
    if record is None:
        response["message"] = "Invalid Transaction Id"
        return _response_script(response)

    check = await service.check_and_update_payment_status(
        body.transaction_id, body.session_id
    )
    if check.get("status"):
        response = {
            "status": True,
            "message": "Success",
            "paid_amount": check.get("paid_amount") or 0,
        }
    else:
        response["message"] = check.get("message") or "Payment failed"
    return _response_script(response)


@payment_gateway_router.post(
    "/payment_response/{transaction_id}",
    summary="Payment callback by path",
    name="Payment Gateway Response Path",
)
async def payment_response_post_path(
    transaction_id: str,
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
    request: Request,
) -> HTMLResponse:
    session_id = request.query_params.get("session_id")
    return await payment_response_post(
        service,
        PaymentResponseBody(transaction_id=transaction_id, session_id=session_id),
    )


@payment_gateway_router.get(
    "/payment_response/{transaction_id}",
    summary="Payment callback (Razorpay return URL)",
    name="Payment Gateway Response Get",
    include_in_schema=False,
)
async def payment_response_get(
    transaction_id: str,
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
    session_id: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    return await payment_response_post(
        service,
        PaymentResponseBody(transaction_id=transaction_id, session_id=session_id),
    )


@payment_gateway_router.post(
    "/payment_js_lib",
    summary="CustomPaymentGateway JS helper",
    name="Payment Gateway JS Lib",
)
async def payment_js_lib_post(
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
) -> PlainTextResponse:
    return _js_lib(service.payment_js_lib_base_url())


@payment_gateway_router.get(
    "/payment_js_lib",
    summary="CustomPaymentGateway JS helper (GET)",
    name="Payment Gateway JS Lib Get",
    include_in_schema=False,
)
async def payment_js_lib_get(
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
) -> PlainTextResponse:
    return _js_lib(service.payment_js_lib_base_url())


@payment_gateway_router.post(
    "/status",
    response_model=ApiSuccessResponse[PaymentStatusResult] | ApiErrorResponse,
    summary="Fully-paid check for booking gate",
    name="Payment Gateway Status",
)
async def payment_status(
    service: Annotated[PaymentGatewayService, Depends(build_payment_gateway_service)],
    body: Annotated[PaymentStatusBody, Body(...)],
) -> ApiSuccessResponse[PaymentStatusResult] | ApiErrorResponse:
    paid = await service.get_payment_status(body.app_reference)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaymentStatusResult(
            paid=paid,
            message="Success" if paid else "Payment not completed",
        ),
    )
