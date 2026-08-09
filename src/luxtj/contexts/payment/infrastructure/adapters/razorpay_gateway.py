"""Razorpay payment adapter — Orders API + Checkout modal + payment verify."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from httpx import AsyncClient

from luxtj.contexts.integration.domain.catalog import credential_value

_RAZORPAY_API = "https://api.razorpay.com/v1"
# Currencies that do not use a fractional subunit with Razorpay.
_ZERO_DECIMAL = frozenset(
    {
        "BIF",
        "CLP",
        "DJF",
        "GNF",
        "JPY",
        "KMF",
        "KRW",
        "MGA",
        "PYG",
        "RWF",
        "UGX",
        "VND",
        "VUV",
        "XAF",
        "XOF",
        "XPF",
    }
)


def _to_minor_units(amount: float, currency: str) -> int:
    cur = (currency or "INR").upper()
    if cur in _ZERO_DECIMAL:
        return int(round(amount))
    return int(round(float(amount) * 100))


def _from_minor_units(amount_minor: int | float, currency: str) -> float:
    cur = (currency or "INR").upper()
    if cur in _ZERO_DECIMAL:
        return float(amount_minor)
    return round(float(amount_minor) / 100.0, 2)


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
        self._company = credential_value(configs, "Company Name") or "LuxTJ"
        self._api_type = str(cfg.get("api_type") or "") or None
        self._currency = (str(cfg.get("currency") or "INR") or "INR").upper()

    def _auth(self) -> tuple[str, str]:
        return self._api_key, self._api_secret

    async def initiate_payment(self, pg_data: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key or not self._api_secret:
            return {
                "status": False,
                "message": "Razorpay credentials missing in integration registry",
            }

        currency = (str(pg_data.get("currency") or self._currency) or "INR").upper()
        amount_major = float(pg_data.get("amount") or 0)
        if amount_major <= 0:
            return {"status": False, "message": "Invalid payment amount"}

        amount_minor = _to_minor_units(amount_major, currency)
        merchant_txn = str(pg_data.get("merchantTransactionId") or "").strip()
        receipt = merchant_txn[:40] if merchant_txn else None
        payload = {
            "amount": amount_minor,
            "currency": currency,
            "receipt": receipt,
            "notes": {
                "merchant_transaction_id": merchant_txn,
                "productinfo": str(pg_data.get("productinfo") or "Booking")[:200],
            },
        }

        try:
            res = await self._http.post(
                f"{_RAZORPAY_API}/orders",
                json=payload,
                auth=self._auth(),
                timeout=30.0,
            )
        except Exception as exc:  # noqa: BLE001
            return {"status": False, "message": f"Razorpay order create failed: {exc}"}

        body: dict[str, Any]
        try:
            body = res.json() if res.content else {}
        except Exception:  # noqa: BLE001
            body = {}
        if res.status_code >= 400 or not isinstance(body, dict) or not body.get("id"):
            message = (
                (body.get("error") or {}).get("description")
                if isinstance(body.get("error"), dict)
                else None
            )
            return {
                "status": False,
                "message": message or f"Razorpay order create failed ({res.status_code})",
                "data": {"request": payload, "response": body},
            }

        order_id = str(body["id"])
        payment_data = {
            "mode": "checkout_modal",
            "pg_code": self.code,
            "key_id": self._api_key,
            "order_id": order_id,
            "amount": amount_minor,
            "currency": currency,
            "name": self._company,
            "description": str(pg_data.get("productinfo") or "Booking"),
            "prefill": {
                "name": str(pg_data.get("firstname") or ""),
                "email": str(pg_data.get("email") or ""),
                "contact": str(pg_data.get("phone") or ""),
            },
            "notes": {
                "merchant_transaction_id": merchant_txn,
            },
            # Kept for redirect-style gateways / legacy clients.
            "checkoutSessionUrl": None,
        }
        return {
            "status": True,
            "message": "Order created",
            "data": {
                "pg_reference_id": order_id,
                "payment_data": payment_data,
                "request": payload,
                "response": body,
            },
        }

    def _verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        if not self._api_secret or not order_id or not payment_id or not signature:
            return False
        digest = hmac.new(
            self._api_secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    async def check_payment_status(
        self,
        pg_reference_id: str,
        gateway_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._api_key or not self._api_secret:
            return {
                "status": False,
                "message": "Razorpay credentials missing in integration registry",
                "payment_status": "pending",
                "data": {"pg_reference_id": pg_reference_id},
            }

        gw = gateway_response if isinstance(gateway_response, dict) else {}
        payment_id = str(
            gw.get("razorpay_payment_id")
            or gw.get("payment_id")
            or gw.get("pg_payment_id")
            or ""
        ).strip()
        order_id = str(
            gw.get("razorpay_order_id")
            or gw.get("order_id")
            or pg_reference_id
            or ""
        ).strip()
        signature = str(
            gw.get("razorpay_signature") or gw.get("signature") or gw.get("pg_signature") or ""
        ).strip()

        if payment_id and order_id and signature:
            if not self._verify_signature(order_id, payment_id, signature):
                return {
                    "status": False,
                    "message": "Invalid Razorpay payment signature",
                    "payment_status": "failed",
                    "data": {"order_id": order_id, "payment_id": payment_id},
                }

        payment: dict[str, Any] | None = None
        if payment_id:
            payment = await self._fetch_payment(payment_id)
        elif order_id:
            payment = await self._fetch_captured_payment_for_order(order_id)

        if not payment:
            return {
                "status": False,
                "message": "Payment not completed",
                "payment_status": "pending",
                "data": {"order_id": order_id, "payment_id": payment_id or None},
            }

        status = str(payment.get("status") or "").lower()
        if status not in {"captured", "authorized"}:
            return {
                "status": False,
                "message": f"Razorpay payment status is {status or 'unknown'}",
                "payment_status": status or "failed",
                "data": payment,
            }

        currency = str(payment.get("currency") or self._currency or "INR").upper()
        amount_major = _from_minor_units(int(payment.get("amount") or 0), currency)
        return {
            "status": True,
            "message": "Success",
            "amount": amount_major,
            "merchantTransactionId": str(
                (payment.get("notes") or {}).get("merchant_transaction_id")
                if isinstance(payment.get("notes"), dict)
                else ""
            )
            or None,
            "data": payment,
        }

    async def _fetch_payment(self, payment_id: str) -> dict[str, Any] | None:
        try:
            res = await self._http.get(
                f"{_RAZORPAY_API}/payments/{payment_id}",
                auth=self._auth(),
                timeout=30.0,
            )
        except Exception:  # noqa: BLE001
            return None
        try:
            body = res.json() if res.content else {}
        except Exception:  # noqa: BLE001
            return None
        if res.status_code >= 400 or not isinstance(body, dict):
            return None
        return body

    async def refund_payment(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key or not self._api_secret:
            return {
                "status": False,
                "message": "Razorpay credentials missing in integration registry",
            }

        payment_id = str(data.get("payment_id") or "").strip()
        if not payment_id:
            return {"status": False, "message": "Razorpay payment_id is required for refund"}

        currency = (str(data.get("currency") or self._currency) or "INR").upper()
        amount_major = float(data.get("amount") or 0)
        if amount_major <= 0:
            return {"status": False, "message": "Invalid refund amount"}

        payload: dict[str, Any] = {
            "amount": _to_minor_units(amount_major, currency),
        }
        notes = data.get("notes")
        if isinstance(notes, dict) and notes:
            payload["notes"] = {str(k): str(v)[:512] for k, v in notes.items()}
        receipt = str(data.get("receipt") or "").strip()
        if receipt:
            payload["receipt"] = receipt[:40]

        try:
            res = await self._http.post(
                f"{_RAZORPAY_API}/payments/{payment_id}/refund",
                json=payload,
                auth=self._auth(),
                timeout=45.0,
            )
        except Exception as exc:  # noqa: BLE001
            return {"status": False, "message": f"Razorpay refund failed: {exc}"}

        body: dict[str, Any]
        try:
            body = res.json() if res.content else {}
        except Exception:  # noqa: BLE001
            body = {}

        if res.status_code >= 400 or not isinstance(body, dict) or not body.get("id"):
            # Pass Razorpay's error through unchanged for admin display.
            message = ""
            err = body.get("error") if isinstance(body, dict) else None
            if isinstance(err, dict):
                message = str(err.get("description") or "").strip()
                if not message:
                    message = str(err.get("code") or "").strip()
                if not message:
                    try:
                        message = json.dumps(err, default=str)
                    except Exception:  # noqa: BLE001
                        message = str(err)
            elif isinstance(err, str) and err.strip():
                message = err.strip()
            elif isinstance(body, dict) and body:
                try:
                    message = json.dumps(body, default=str)
                except Exception:  # noqa: BLE001
                    message = str(body)
            return {
                "status": False,
                "message": message or f"Razorpay refund failed ({res.status_code})",
                "data": {"request": payload, "response": body},
            }

        refund_amount = _from_minor_units(int(body.get("amount") or payload["amount"]), currency)
        return {
            "status": True,
            "message": "Refund processed",
            "refund_id": str(body.get("id") or ""),
            "amount": refund_amount,
            "data": {"request": payload, "response": body},
        }

    async def _fetch_captured_payment_for_order(
        self, order_id: str
    ) -> dict[str, Any] | None:
        try:
            res = await self._http.get(
                f"{_RAZORPAY_API}/orders/{order_id}/payments",
                auth=self._auth(),
                timeout=30.0,
            )
        except Exception:  # noqa: BLE001
            return None
        try:
            body = res.json() if res.content else {}
        except Exception:  # noqa: BLE001
            return None
        if res.status_code >= 400 or not isinstance(body, dict):
            return None
        items = body.get("items") if isinstance(body.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get("status") or "").lower() in {"captured", "authorized"}:
                return item
        return None
