"""Payment gateway SPI (adapter contract)."""

from typing import Any, Protocol


class PaymentGateway(Protocol):
    """Contract for payment gateway adapters (Razorpay)."""

    code: str

    async def initiate_payment(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create remote checkout/session.

        Expected ``data`` keys: merchantTransactionId, amount, currency, email,
        firstname, phone, productinfo, success_url, cancel_url.

        Success return shape::
            {status: True, message?, data: {pg_reference_id, payment_data, request, response}}
        """
        ...

    async def check_payment_status(self, pg_reference_id: str) -> dict[str, Any]:
        """
        Verify payment with the gateway.

        Success return shape::
            {status: True, message, amount, merchantTransactionId, data}
        Amount is in major currency units (not cents).
        """
        ...
