"""Hotel pre-book quote — mirrors HotelPreBookQuote."""

from __future__ import annotations

from typing import Any

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.hotel.application.promo import HotelPromo
from sqlalchemy.ext.asyncio import AsyncSession


class HotelPreBookQuote:
    @staticmethod
    def supplier_pricing_baseline(room: dict[str, Any], list_inner: dict[str, Any]) -> dict[str, Any]:
        currency = str(list_inner.get("currency") or room.get("currency") or "USD").upper()
        extra_fees = room.get("extraFees") if isinstance(room.get("extraFees"), list) else []
        extra_fees_sum = 0.0
        for fee in extra_fees:
            if isinstance(fee, dict):
                extra_fees_sum += float(fee.get("amount") or 0)

        if room.get("amount") is not None and isinstance(room.get("amount"), (int, float)):
            sub_total = max(0.0, float(room["amount"]))
        else:
            base_fare = float(room.get("BaseFare") or 0)
            taxes_legacy = float(room.get("TotalTax") or room.get("taxes") or 0)
            sub_total = max(0.0, base_fare + taxes_legacy + extra_fees_sum)

        prepaid = max(0.0, sub_total - extra_fees_sum)
        taxes = float(room.get("TotalTax") or room.get("taxes") or 0)
        room_rate_exclusive = max(0.0, prepaid - taxes)
        discount_block = room.get("Discount")
        supplier_discount = 0.0
        if isinstance(discount_block, dict):
            supplier_discount = max(0.0, float(discount_block.get("amount") or 0))
        payable = max(0.0, prepaid - supplier_discount)
        return {
            "currency": currency,
            "extra_fees_sum": round(extra_fees_sum, 2),
            "sub_total_supplier": round(sub_total, 2),
            "prepaid_room_supplier": round(prepaid, 2),
            "taxes_supplier": round(taxes, 2),
            "room_rate_exclusive_supplier": round(room_rate_exclusive, 2),
            "supplier_discount": round(supplier_discount, 2),
            "payable_after_supplier_discount": round(payable, 2),
        }

    @staticmethod
    async def compute(
        session: AsyncSession,
        room: dict[str, Any],
        list_inner: dict[str, Any],
        promo_code: str | None,
        admin_markup: float,
        payment_gateway: Any | None,
    ) -> dict[str, Any]:
        b = HotelPreBookQuote.supplier_pricing_baseline(room, list_inner)
        currency = b["currency"]
        payable_after_supplier = b["payable_after_supplier_discount"]

        promo_discount = 0.0
        promo_code_applied = None
        promo_offer_valid = False
        promo_discount_type = None
        promo_rule_amount = None
        trim_promo = (promo_code or "").strip()
        rate = float(AdminCurrency.rate_to_admin_or_one(currency))
        if trim_promo:
            payable_admin = round(payable_after_supplier * rate, 2)
            eval_result = await HotelPromo.evaluate(session, trim_promo, payable_admin)
            if eval_result.get("applicable"):
                promo_offer_valid = True
                promo_code_applied = eval_result["promo_code"]
                promo_discount_admin = float(eval_result["discount_amount_admin"])
                promo_discount = (
                    round(promo_discount_admin / rate, 2) if rate > 0 else round(promo_discount_admin, 2)
                )
                promo_discount_type = eval_result["discount_type"]
                rule_val = float(eval_result["discount_rule_value"])
                promo_rule_amount = (
                    round(rule_val, 2)
                    if promo_discount_type == "percentage"
                    else (round(rule_val / rate, 2) if rate > 0 else round(rule_val, 2))
                )

        payable_after_promo = max(0.0, round(payable_after_supplier - promo_discount, 2))
        embedded_mk = max(0.0, round(float(room.get("_teenva_admin_markup") or 0), 2))
        request_mk = max(0.0, round(float(admin_markup), 2))
        payable_before_convenience = max(0.0, round(payable_after_promo + request_mk, 2))
        conv = HotelPreBookQuote.convenience_amount(payment_gateway, payable_before_convenience)
        total_charge = max(0.0, round(payable_before_convenience + conv["amount"], 2))
        quote = {
            **b,
            "promo_discount": round(promo_discount, 2),
            "admin_markup": round(embedded_mk + request_mk, 2),
            "payable_before_convenience": payable_before_convenience,
            "convenience_fee": conv["amount"],
            "convenience_type": conv["type"],
            "convenience_value_raw": conv["raw"],
            "total_charge": total_charge,
            "promo_code_applied": promo_code_applied,
            "promo_offer_valid": promo_offer_valid,
            "promo_discount_type": promo_discount_type,
            "promo_rule_amount": round(promo_rule_amount, 2) if promo_rule_amount is not None else None,
            "currency_conversion_rate": rate,
            "admin_currency": AdminCurrency.code(),
        }
        return AdminCurrency.apply_hotel_pre_book_quote_admin_base(
            quote, admin_markup, payment_gateway
        )

    @staticmethod
    def count_guests(room: dict[str, Any]) -> tuple[int, int, int]:
        adults = 0
        children = 0
        room_count = 1
        if isinstance(room.get("paxData"), list) and room["paxData"]:
            for row in room["paxData"]:
                if not isinstance(row, dict):
                    continue
                adults += int(row.get("Adult") or 0)
                children += int(row.get("Child") or 0)
        elif isinstance(room.get("rooms"), list) and room["rooms"]:
            room_count = max(1, len(room["rooms"]))
            for r in room["rooms"]:
                if not isinstance(r, dict):
                    continue
                adults += int(r.get("adultCount") or 0)
                children += int(r.get("childCount") or 0)
        if adults + children < 1:
            adults = 1
        return room_count, adults, children

    @staticmethod
    def convenience_amount(pg: Any | None, base_payable: float) -> dict[str, Any]:
        if pg is None:
            return {"amount": 0.0, "type": None, "raw": 0.0}
        raw = float(getattr(pg, "convenience_value", None) or 0)
        if raw <= 0:
            return {"amount": 0.0, "type": None, "raw": 0.0}
        ctype = str(getattr(pg, "convenience_type", None) or "flat").lower()
        if ctype == "percentage":
            return {
                "amount": round((raw * base_payable) / 100, 2),
                "type": "percentage",
                "raw": raw,
            }
        return {"amount": round(raw, 2), "type": "flat", "raw": raw}
