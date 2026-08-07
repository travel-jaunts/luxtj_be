"""Payment gateway orchestrator — create, initiate, verify, status gate."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

from httpx import AsyncClient

from luxtj.bootstrap import config
from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.integration.domain.catalog import PAYMENT_GATEWAYS
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
    ) -> dict[str, Any]:
        record = await self.read_payment_record(transaction_id)
        if record is None:
            return {"status": False, "message": "Invalid transaction"}

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
            return {"status": False, "message": "Payment gateway not available"}

        pg_response = await gateway.check_payment_status(pg_reference_id)
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
                }
            await self.update_payment_record_status(
                transaction_id, "accepted", pg_response.get("data") or {}
            )
            return {
                "status": True,
                "message": "Success",
                "paid_amount": float(amount),
            }

        await self.update_payment_record_status(
            transaction_id, "declined", pg_response.get("data") or {}
        )
        return {
            "status": False,
            "message": pg_response.get("message") or "Payment failed",
        }
