"""Payment gateway orchestrator — create, initiate, verify, status gate."""

from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

from httpx import AsyncClient

from luxtj.bootstrap import config
from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.integration.domain.catalog import PAYMENT_GATEWAYS, gateway_supports_refund_api
from luxtj.contexts.integration.domain.entities import PaymentGateway as RegistryPaymentGateway
from luxtj.contexts.integration.infrastructure.registry_cache import (
    IntegrationRegistryCache,
    get_integration_registry,
)
from luxtj.contexts.payment.application.ports import PaymentGatewayTransactionRepository
from luxtj.contexts.payment.domain.gateway import PaymentGateway
from luxtj.contexts.payment.domain.transaction import PaymentGatewayTransaction
from luxtj.contexts.payment.infrastructure.adapters.razorpay_gateway import RazorpayPaymentGateway


class PaymentGatewayService:
    def __init__(
        self,
        *,
        repository: PaymentGatewayTransactionRepository,
        http_client: AsyncClient,
        registry: IntegrationRegistryCache | None = None,
        base_url: str | None = None,
    ) -> None:
        self._repo = repository
        self._http = http_client
        self._registry = registry or get_integration_registry()
        self._base_url = (base_url or config.PUBLIC_BASE_URL).rstrip("/")

    def _public_url(self, path: str) -> str:
        return urljoin(f"{self._base_url}/", path.lstrip("/"))

    def get_active_payment_gateways(self) -> list[RegistryPaymentGateway]:
        return [
            pg
            for pg in self._registry.list_active_payment_gateways()
            if pg.code in PAYMENT_GATEWAYS
        ]

    def get_active_payment_gateways_for_api(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for pg in self.get_active_payment_gateways():
            fee_raw = pg.convenience_value
            fee = Decimal("0") if fee_raw in (None, "") else Decimal(str(fee_raw))
            fee_type = str(pg.convenience_type or "flat").lower()
            convenience_fee_type = "percentage" if fee_type == "percentage" else "flat"
            result.append(
                {
                    "code": pg.code,
                    "name": pg.name,
                    "convinience_fee": float(fee),
                    "convinience_fee_type": convenience_fee_type,
                    "logo": self._public_url(f"images/payment-gateways/{pg.code}.png"),
                }
            )
        return result

    def get_default_gateway_code(self) -> str | None:
        gateways = self.get_active_payment_gateways()
        return gateways[0].code if gateways else None

    def get_gateway_by_code(self, code: str) -> PaymentGateway | None:
        code_l = code.lower()
        if code_l not in PAYMENT_GATEWAYS:
            return None
        pg = self._registry.resolve_payment_gateway(code_l)
        if pg is None:
            return None
        configuration = pg.runtime_configuration()
        if code_l == "razorpay":
            return RazorpayPaymentGateway(
                http_client=self._http,
                configuration=configuration,
            )
        return None

    def payment_url_for(self, transaction_id: str) -> str:
        return self._public_url(f"v1/payment-gateway/payment/{transaction_id}")

    def payment_response_url_for(self, transaction_id: str) -> str:
        return self._public_url(f"v1/payment-gateway/payment_response/{transaction_id}")

    def payment_js_lib_base_url(self) -> str:
        return self._public_url("v1/payment-gateway/payment")

    async def create_payment_record(
        self,
        *,
        app_reference: str,
        pg_code: str | None,
        currency: str,
        booking_amount: Decimal | float,
        amount: Decimal | float,
        firstname: str,
        email: str,
        phone: str,
        productinfo: str,
        flight_booking_details_id: str | None = None,
    ) -> dict[str, Any]:
        gateways = self.get_active_payment_gateways()
        if not gateways:
            return {"status": False, "message": "No payment gateway active"}

        if pg_code:
            pg = next((g for g in gateways if g.code == pg_code.lower()), None)
        else:
            pg = gateways[0]
        if pg is None:
            return {"status": False, "message": "Payment gateway not found or inactive"}

        admin = AdminCurrency.code()
        cur_in = (currency or "").strip().upper()[:3] or admin
        booking_dec = Decimal(str(booking_amount))
        amount_dec = Decimal(str(amount))
        fx = Decimal("1")
        if cur_in != admin:
            fx = Decimal(str(AdminCurrency.rate_to_admin_or_one(cur_in)))
            booking_dec = (booking_dec * fx).quantize(Decimal("0.01"))
            amount_dec = (amount_dec * fx).quantize(Decimal("0.01"))

        count = await self._repo.count_by_app_reference(app_reference)
        transaction_id = f"{app_reference}-{count}"
        request_params = {
            "txnid": transaction_id,
            "amount": float(amount_dec),
            "firstname": firstname,
            "email": email,
            "phone": phone,
            "productinfo": productinfo,
        }
        entity = PaymentGatewayTransaction.create_pending(
            transaction_id=transaction_id,
            app_reference=app_reference,
            pg_code=pg.code,
            amount=amount_dec,
            booking_amount=booking_dec,
            currency=admin,
            request_params=request_params,
            pg_currency_conversion_rate=fx,
            flight_booking_details_id=flight_booking_details_id,
        )
        await self._repo.add(entity)
        return {
            "status": True,
            "transaction_id": transaction_id,
            "payment_url": self.payment_url_for(transaction_id),
            "pg_code": pg.code,
            "app_reference": app_reference,
        }

    async def create_and_initiate_payment(
        self,
        *,
        app_reference: str,
        pg_code: str | None,
        currency: str,
        booking_amount: Decimal | float,
        amount: Decimal | float,
        firstname: str,
        email: str,
        phone: str,
        productinfo: str,
        flight_booking_details_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a pending txn row then create the gateway order/session."""
        created = await self.create_payment_record(
            app_reference=app_reference,
            pg_code=pg_code,
            currency=currency,
            booking_amount=booking_amount,
            amount=amount,
            firstname=firstname,
            email=email,
            phone=phone,
            productinfo=productinfo,
            flight_booking_details_id=flight_booking_details_id,
        )
        if not created.get("status"):
            return created

        transaction_id = str(created["transaction_id"])
        initiated = await self.initiate_payment_for_transaction(transaction_id)
        if not initiated.get("status"):
            await self.update_payment_record_status(
                transaction_id,
                "declined",
                {"initiate_error": initiated.get("message")},
            )
            return {
                "status": False,
                "message": initiated.get("message") or "Payment initiation failed",
                "transaction_id": transaction_id,
                "app_reference": app_reference,
                "pg_code": created.get("pg_code"),
            }

        data = initiated.get("data") if isinstance(initiated.get("data"), dict) else {}
        payment_data = (
            data.get("payment_data") if isinstance(data.get("payment_data"), dict) else {}
        )
        mode = str(payment_data.get("mode") or "").strip()
        if not mode:
            mode = "redirect" if payment_data.get("checkoutSessionUrl") else "checkout_modal"

        return {
            "status": True,
            "transaction_id": transaction_id,
            "payment_url": created.get("payment_url"),
            "pg_code": created.get("pg_code"),
            "app_reference": app_reference,
            "pg_reference_id": data.get("pg_reference_id"),
            "payment": {
                "mode": mode,
                "pg_code": created.get("pg_code"),
                "pg_reference_id": data.get("pg_reference_id"),
                "checkout": payment_data,
            },
        }

    async def read_payment_record(
        self, transaction_id: str
    ) -> PaymentGatewayTransaction | None:
        return await self._repo.get_by_transaction_id(transaction_id)

    async def update_payment_record_status(
        self,
        transaction_id: str,
        status: str,
        response_params: dict[str, Any] | list | None = None,
    ) -> None:
        await self._repo.update_status(transaction_id, status, response_params)

    async def update_pg_reference_id(self, transaction_id: str, pg_reference_id: str) -> None:
        await self._repo.update_pg_reference_id(transaction_id, pg_reference_id)

    async def get_payment_status(self, app_reference: str) -> bool:
        if config.BYPASS_PAYMENT:
            return True
        accepted = await self._repo.list_accepted_by_app_reference(app_reference)
        all_rows = await self._repo.list_by_app_reference(app_reference)
        booking_amount = all_rows[0].booking_amount if all_rows else Decimal("0")
        paid_amount = sum((row.amount for row in accepted), Decimal("0"))
        return booking_amount > 0 and paid_amount >= booking_amount

    async def initiate_payment_for_transaction(self, transaction_id: str) -> dict[str, Any]:
        record = await self.read_payment_record(transaction_id)
        if record is None:
            return {"status": False, "message": "Invalid transaction"}

        gateway = self.get_gateway_by_code(record.pg_code)
        if gateway is None:
            return {"status": False, "message": "Payment gateway not available"}

        success_url = self.payment_response_url_for(transaction_id)
        cancel_url = success_url

        params = record.request_params
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                params = {}
        if not isinstance(params, dict):
            params = {}

        pg_data = {
            "merchantTransactionId": transaction_id,
            "amount": float(record.pg_amount or record.amount),
            "currency": record.pg_currency or record.currency,
            "email": params.get("email") or "",
            "firstname": params.get("firstname") or "",
            "phone": params.get("phone") or "",
            "productinfo": params.get("productinfo") or "Booking",
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        result = await gateway.initiate_payment(pg_data)
        if not result.get("status"):
            return result
        data = result.get("data") or {}
        pg_ref = data.get("pg_reference_id")
        if pg_ref:
            await self.update_pg_reference_id(transaction_id, str(pg_ref))
        return result

    async def check_and_update_payment_status(
        self,
        transaction_id: str,
        pg_reference_id_from_request: str | None = None,
        gateway_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = await self.read_payment_record(transaction_id)
        if record is None:
            return {
                "status": False,
                "message": "Invalid transaction",
                "app_reference": None,
                "transaction_id": transaction_id,
            }

        if record.is_accepted():
            return {
                "status": True,
                "message": "Already paid",
                "paid_amount": float(record.amount),
                "app_reference": record.app_reference,
                "transaction_id": transaction_id,
                "pg_code": record.pg_code,
                "paid": True,
            }

        pg_reference_id = (
            pg_reference_id_from_request
            or record.pg_reference_id
            or transaction_id
        )
        if (
            pg_reference_id_from_request
            and pg_reference_id_from_request != (record.pg_reference_id or "")
        ):
            await self.update_pg_reference_id(transaction_id, pg_reference_id_from_request)

        gateway = self.get_gateway_by_code(record.pg_code)
        if gateway is None:
            return {
                "status": False,
                "message": "Payment gateway not available",
                "app_reference": record.app_reference,
                "transaction_id": transaction_id,
                "pg_code": record.pg_code,
                "paid": False,
            }

        pg_response = await gateway.check_payment_status(
            pg_reference_id,
            gateway_response=gateway_response,
        )
        if pg_response.get("status"):
            amount = Decimal(str(pg_response.get("amount") or 0))
            expected = Decimal(str(record.pg_amount or 0))
            if abs(amount - expected) > Decimal("0.01"):
                await self.update_payment_record_status(
                    transaction_id, "declined", pg_response.get("data") or {}
                )
                return {
                    "status": False,
                    "message": "Payment validation failed. Please contact support.",
                    "app_reference": record.app_reference,
                    "transaction_id": transaction_id,
                    "pg_code": record.pg_code,
                    "paid": False,
                }
            await self.update_payment_record_status(
                transaction_id, "accepted", pg_response.get("data") or {}
            )
            return {
                "status": True,
                "message": "Success",
                "paid_amount": float(amount),
                "app_reference": record.app_reference,
                "transaction_id": transaction_id,
                "pg_code": record.pg_code,
                "paid": True,
            }

        payment_status = str(pg_response.get("payment_status") or "").lower()
        message = str(pg_response.get("message") or "Payment failed")
        # Keep row pending when gateway still reports unpaid (same order can be retried).
        # Decline on hard failures / bad signature / explicit failed statuses.
        hard_fail = payment_status in {
            "failed",
            "cancelled",
            "canceled",
            "refunded",
        } or "signature" in message.lower()
        if hard_fail:
            await self.update_payment_record_status(
                transaction_id, "declined", pg_response.get("data") or {}
            )

        return {
            "status": False,
            "message": message,
            "app_reference": record.app_reference,
            "transaction_id": transaction_id,
            "pg_code": record.pg_code,
            "paid": False,
            "payment_status": payment_status or None,
        }

    async def revalidate_payment_status(
        self,
        *,
        transaction_id: str,
        pg_reference_id: str | None = None,
        gateway_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Common cross-module payment revalidation.

        Verifies with the gateway adapter, updates DB status, and returns a
        payload booking modules can gate ProcessBooking on.
        """
        check = await self.check_and_update_payment_status(
            transaction_id,
            pg_reference_id_from_request=pg_reference_id,
            gateway_response=gateway_response,
        )
        app_ref = check.get("app_reference")
        fully_paid = False
        if app_ref:
            fully_paid = await self.get_payment_status(str(app_ref))
        return {
            **check,
            "paid": bool(check.get("status")) and fully_paid,
            "fully_paid": fully_paid,
        }

    @staticmethod
    def _extract_gateway_payment_id(record: PaymentGatewayTransaction) -> str:
        """Best-effort gateway payment id from stored verify response / request."""
        resp = record.response_params if isinstance(record.response_params, dict) else {}
        for key in ("id", "razorpay_payment_id", "payment_id", "pg_payment_id"):
            value = str(resp.get(key) or "").strip()
            if value and not value.startswith("order_"):
                return value
        # Nested shapes from verify payload
        for nest_key in ("data", "payment", "payload"):
            nested = resp.get(nest_key)
            if isinstance(nested, dict):
                for key in ("id", "razorpay_payment_id", "payment_id"):
                    value = str(nested.get(key) or "").strip()
                    if value and not value.startswith("order_"):
                        return value
        req = record.request_params if isinstance(record.request_params, dict) else {}
        for key in ("razorpay_payment_id", "payment_id"):
            value = str(req.get(key) or "").strip()
            if value:
                return value
        return ""

    async def issue_refund(
        self,
        *,
        transaction_id: str,
        refund_amount: Decimal | float,
        remark: str | None = None,
        manual_details: str | None = None,
        admin_user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Issue API or manual refund for an accepted (or partially refunded) payment.
        """
        txn_id = str(transaction_id or "").strip()
        record = await self._repo.get_by_transaction_id(txn_id)
        if record is None:
            return {"status": False, "message": "Payment transaction not found"}

        status_l = str(record.status or "").lower()
        if status_l not in {"accepted", "partially_refunded"}:
            return {
                "status": False,
                "message": f"Payment status '{record.status}' is not refundable",
            }

        amount = Decimal(str(refund_amount or 0))
        if amount <= 0:
            return {"status": False, "message": "Refund amount must be greater than zero"}

        remaining = record.refundable_amount()
        if amount > remaining + Decimal("0.001"):
            return {
                "status": False,
                "message": (
                    f"Refund amount must be ≤ refundable amount "
                    f"({float(remaining)} {record.currency})"
                ),
            }

        supports_api = gateway_supports_refund_api(record.pg_code)
        remark_clean = str(remark or "").strip() or None
        manual_clean = str(manual_details or "").strip() or None

        refund_payload: dict[str, Any] = {
            "admin_user_id": admin_user_id,
            "remark": remark_clean,
        }
        gateway_response: dict[str, Any] | None = None
        refund_mode: str

        if supports_api:
            gateway = self.get_gateway_by_code(record.pg_code)
            if gateway is None:
                return {"status": False, "message": "Payment gateway adapter not available"}
            payment_id = self._extract_gateway_payment_id(record)
            if not payment_id:
                return {
                    "status": False,
                    "message": "Gateway payment id missing; cannot call refund API",
                }
            notes: dict[str, Any] = {"app_reference": record.app_reference}
            if remark_clean:
                notes["admin_remark"] = remark_clean
            # Receipt is Razorpay's idempotency key per payment — unique per attempt.
            receipt = f"rf-{uuid.uuid4().hex[:12]}-{int(time.time()) % 10_000_000}"[:40]
            api_result = await gateway.refund_payment(
                {
                    "payment_id": payment_id,
                    "amount": float(amount),
                    "currency": record.currency,
                    "notes": notes,
                    "receipt": receipt,
                }
            )
            if not api_result.get("status"):
                # Surface gateway message (e.g. Razorpay error.description) as-is.
                return {
                    "status": False,
                    "message": str(api_result.get("message") or "Gateway refund failed"),
                    "data": api_result.get("data") or {},
                }
            refund_mode = "api"
            gateway_response = (
                api_result.get("data") if isinstance(api_result.get("data"), dict) else {}
            )
            refund_payload["gateway"] = {
                "refund_id": api_result.get("refund_id"),
                "payment_id": payment_id,
                "response": gateway_response,
            }
            # Prefer amount returned by gateway when present
            try:
                if api_result.get("amount") is not None:
                    amount = Decimal(str(api_result["amount"]))
            except Exception:  # noqa: BLE001
                pass
        else:
            if not manual_clean:
                return {
                    "status": False,
                    "message": (
                        "This payment gateway has no refund API. "
                        "Manual refund details are required."
                    ),
                    "requires_manual_details": True,
                }
            refund_mode = "manual"
            refund_payload["manual_details"] = manual_clean

        new_refunded = Decimal(str(record.refunded_amount or 0)) + amount
        paid = Decimal(str(record.amount or 0))
        if new_refunded + Decimal("0.001") >= paid:
            new_status = "refunded"
            new_refunded = paid
        else:
            new_status = "partially_refunded"

        # Merge prior response with refund trail
        prior = record.response_params if isinstance(record.response_params, dict) else {}
        merged_response = {
            **prior,
            "refund": refund_payload,
        }

        await self._repo.apply_refund(
            txn_id,
            status=new_status,
            refunded_amount=new_refunded,
            refund_remark=remark_clean,
            refund_mode=refund_mode,
            refund_details=refund_payload,
            response_params=merged_response,
        )

        return {
            "status": True,
            "message": "Refund recorded" if refund_mode == "manual" else "Refund processed",
            "transaction_id": txn_id,
            "app_reference": record.app_reference,
            "payment_status": new_status,
            "refund_mode": refund_mode,
            "refunded_amount": float(new_refunded),
            "refund_amount_this_request": float(amount),
            "currency": record.currency,
            "supports_refund_api": supports_api,
        }
