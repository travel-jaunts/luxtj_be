"""Admin / bookkeeping base currency façade (mirrors TeenvaAdminCurrency)."""

from __future__ import annotations

from typing import Any, Protocol

from luxtj.bootstrap import config
from luxtj.contexts.currency.infrastructure.currency_conversion import (
    CurrencyConversionService,
    get_currency_conversion,
)
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle

logger = get_logger_handle(__name__)


class _ConvenienceGateway(Protocol):
    convenience_type: str | None
    convenience_value: float | None


def _convenience_amount(
    payment_gateway: _ConvenienceGateway | None, base_payable: float
) -> dict[str, float | str | None]:
    """Mirrors HotelPreBookQuote::convenienceAmount."""
    if payment_gateway is None:
        return {"amount": 0.0, "type": None, "raw": 0.0}
    raw = float(payment_gateway.convenience_value or 0)
    if raw <= 0:
        return {"amount": 0.0, "type": None, "raw": 0.0}
    conv_type = str(payment_gateway.convenience_type or "flat").lower()
    if conv_type == "percentage":
        return {
            "amount": round((raw * base_payable) / 100, 2),
            "type": "percentage",
            "raw": raw,
        }
    return {"amount": round(raw, 2), "type": "flat", "raw": raw}


class AdminCurrency:
    @staticmethod
    def code() -> str:
        c = (config.ADMIN_CURRENCY or "USD").upper().strip()
        return c if c else "USD"

    @staticmethod
    def _conversion() -> CurrencyConversionService:
        return get_currency_conversion()

    @staticmethod
    def rate_to_admin(from_currency: str) -> float | None:
        """FX multiplier: 1 unit of from_currency → how many units of admin currency."""
        frm = from_currency.upper().strip()
        admin = AdminCurrency.code()
        if frm == "" or frm == admin:
            return 1.0
        return AdminCurrency._conversion().get_rate(frm, admin)

    @staticmethod
    def rate_to_admin_or_one(from_currency: str) -> float:
        """Same as rate_to_admin but never null; logs and returns 1.0 if unavailable."""
        rate = AdminCurrency.rate_to_admin(from_currency)
        if rate is None or rate <= 0:
            logger.warning(
                "AdminCurrency: missing FX rate, using 1:1 from=%s to=%s",
                from_currency,
                AdminCurrency.code(),
            )
            return 1.0
        return rate

    @staticmethod
    def convert_amount_to_admin(amount: float, from_currency: str) -> dict[str, float]:
        rate = AdminCurrency.rate_to_admin_or_one(from_currency)
        return {"amount": round(amount * rate, 2), "rate": rate}

    @staticmethod
    def apply_hotel_pre_book_quote_admin_base(
        quote: dict[str, Any],
        admin_markup: float,
        payment_gateway: _ConvenienceGateway | None = None,
    ) -> dict[str, Any]:
        """
        Normalize hotel pre-book quote to admin: scale supplier lines;
        keep request admin_markup semantics in admin; re-run convenience on admin payable.
        """
        supplier_cur = str(quote.get("currency") or "USD").upper()
        admin = AdminCurrency.code()
        rate = AdminCurrency.rate_to_admin_or_one(supplier_cur)

        def scale(x: float) -> float:
            return round(x * rate, 2)

        quote["supplier_currency"] = supplier_cur
        quote["currency_conversion_rate"] = rate

        for key in (
            "extra_fees_sum",
            "sub_total_supplier",
            "prepaid_room_supplier",
            "taxes_supplier",
            "room_rate_exclusive_supplier",
            "supplier_discount",
            "payable_after_supplier_discount",
            "promo_discount",
        ):
            if key in quote:
                quote[key] = scale(float(quote[key]))

        pdt = str(quote.get("promo_discount_type") or "").lower()
        if (
            pdt != "percentage"
            and "promo_rule_amount" in quote
            and quote["promo_rule_amount"] is not None
        ):
            quote["promo_rule_amount"] = scale(float(quote["promo_rule_amount"]))

        payable_after_promo = max(
            0,
            round(
                float(quote.get("payable_after_supplier_discount") or 0)
                - float(quote.get("promo_discount") or 0),
                2,
            ),
        )
        request_mk_scaled = scale(max(0, round(admin_markup, 2)))
        before_conv = max(0, round(payable_after_promo + request_mk_scaled, 2))

        conv = _convenience_amount(payment_gateway, before_conv)
        quote["admin_markup"] = scale(float(quote.get("admin_markup") or 0))
        quote["payable_before_convenience"] = before_conv
        quote["convenience_fee"] = conv["amount"]
        quote["convenience_type"] = conv["type"]
        quote["convenience_value_raw"] = conv["raw"]
        quote["total_charge"] = max(0, round(before_conv + float(conv["amount"] or 0), 2))
        quote["currency"] = admin
        return quote
