"""Payment gateway SPI (adapter contract)."""

from typing import Any, Protocol


class PaymentGateway(Protocol):
    """Contract for payment gateway adapters (Razorpay, …)."""

    code: str

    async def initiate_payment(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create remote checkout/session/order.

        Expected ``data`` keys: merchantTransactionId, amount, currency, email,
        firstname, phone, productinfo, success_url, cancel_url.

        Success return shape::
            {
              status: True,
              message?,
              data: {
                pg_reference_id,
                payment_data: {
                  mode: "checkout_modal" | "redirect",
                  …gateway-specific checkout fields,
                  checkoutSessionUrl?: str  # redirect gateways
                },
                request,
                response,
              },
            }
        """
        ...

    async def check_payment_status(
        self,
        pg_reference_id: str,
        gateway_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Verify payment with the gateway.

        ``gateway_response`` may carry client-side fields (e.g. Razorpay
        payment_id + signature) needed for verification.

        Success return shape::
            {status: True, message, amount, merchantTransactionId, data}
        Amount is in major currency units (not cents/paise).
        """
        ...

    async def refund_payment(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Issue a refund against a captured payment.

        Expected ``data`` keys: payment_id (gateway payment id), amount (major units),
        currency, notes (optional dict), receipt (optional).

        Success return shape::
            {status: True, message, refund_id?, amount, data: {request, response}}
        """
        ...
