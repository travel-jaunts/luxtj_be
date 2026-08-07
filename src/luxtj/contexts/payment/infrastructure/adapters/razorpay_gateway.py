"""Razorpay payment adapter — credentials from integration registry only."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from luxtj.contexts.integration.domain.catalog import credential_value


class RazorpayPaymentGateway:
    code = "razorpay"

    def __init__(
        self,
        *,
        http_client: AsyncClient,
        configuration: dict[str, Any],
    ) -> None:
        self._http = http_client
        cfg = configuration or {}
        configs = cfg.get("configs") if isinstance(cfg.get("configs"), dict) else {}
        self._api_key = credential_value(configs, "API Key")
        self._api_secret = credential_value(configs, "API Secret")
        self._company = credential_value(configs, "Company Name")
        self._api_type = str(cfg.get("api_type") or "") or None
        self._currency = str(cfg.get("currency") or "") or None

    async def initiate_payment(self, pg_data: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key or not self._api_secret:
            return {
                "status": False,
                "message": "Razorpay credentials missing in integration registry",
            }
        # Placeholder until Razorpay Orders + Checkout is wired end-to-end.
        return {
            "status": False,
            "message": "Razorpay adapter not fully configured for live checkout yet",
            "data": {
                "pg_code": self.code,
                "company": self._company,
                "api_type": self._api_type,
                "currency": self._currency,
            },
        }

    async def check_payment_status(self, pg_reference_id: str) -> dict[str, Any]:
        return {
            "status": False,
            "message": "Razorpay verification not implemented",
            "payment_status": "pending",
            "data": {"pg_reference_id": pg_reference_id},
        }
