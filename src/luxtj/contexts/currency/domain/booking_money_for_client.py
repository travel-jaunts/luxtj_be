"""Reverse FX helpers for client-facing booking money (admin → booking currency)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency


class BookingMoneyForClient:
    @staticmethod
    def strip_admin_markup_from_flight_price_block(price: dict[str, Any]) -> dict[str, Any]:
        breakup = price.get("PriceBreakup")
        if isinstance(breakup, dict):
            breakup.pop("AdminMarkup", None)
        return price

    @staticmethod
    def strip_admin_markup_from_flight_row(flight: dict[str, Any]) -> dict[str, Any]:
        price = flight.get("Price")
        if isinstance(price, dict):
            flight["Price"] = BookingMoneyForClient.strip_admin_markup_from_flight_price_block(
                price
            )
        return flight

    @staticmethod
    def admin_to_booking_amount(admin_amount: float, booking_to_admin_rate: float) -> float:
        if booking_to_admin_rate <= 0:
            return round(admin_amount, 2)
        return round(admin_amount / booking_to_admin_rate, 2)

    @staticmethod
    def convert_flight_price_from_admin_to_booking(
        price: dict[str, Any],
        *,
        currency_conversion_rate: float | None = None,
        supplier_currency: str | None = None,
    ) -> dict[str, Any]:
        admin = AdminCurrency.code()
        rate = (
            float(currency_conversion_rate)
            if currency_conversion_rate is not None
            else float(price.get("currency_conversion_rate") or 1)
        )
        supplier_raw = supplier_currency or price.get("supplier_currency") or ""
        supplier = str(supplier_raw).upper().strip()

        if supplier == "" or rate <= 0 or supplier == admin.upper():
            code = supplier or str(price.get("Currency") or price.get("currency") or admin).upper()
            if code == "":
                code = admin
            price["Currency"] = code
            price["currency"] = code
            price["currency_conversion_rate"] = 1.0
            return price

        sc: Callable[[float], float] = lambda x: BookingMoneyForClient.admin_to_booking_amount(
            x, rate
        )

        for key in (
            "basic_fare",
            "taxes_and_fees",
            "taxes_and_surcharges",
            "TotalDisplayFare",
            "admin_discount",
            "discount_amount",
            "convenience_fee_amount",
            "total_seat_price",
            "SupplierDiscount",
        ):
            if key in price and isinstance(price[key], (int, float)):
                price[key] = sc(float(price[key]))

        if isinstance(price.get("PriceBreakup"), dict):
            pb = dict(price["PriceBreakup"])
            for key in ("BasicFare", "Tax", "AdminMarkup"):
                if key in pb and isinstance(pb[key], (int, float)):
                    pb[key] = sc(float(pb[key]))
            price["PriceBreakup"] = pb

        if isinstance(price.get("PassengerBreakup"), dict):
            price["PassengerBreakup"] = BookingMoneyForClient._scale_flight_passenger_breakup(
                price["PassengerBreakup"], sc
            )

        price["Currency"] = supplier
        price["currency"] = supplier
        price["currency_conversion_rate"] = 1.0
        return price

    @staticmethod
    def _scale_flight_passenger_breakup(
        pb: dict[str, Any], sc: Callable[[float], float]
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for pax_type, row in pb.items():
            if not isinstance(row, dict):
                out[pax_type] = row
                continue
            copy = dict(row)
            for key in ("BasePrice", "Tax", "TotalPrice"):
                if key in copy and isinstance(copy[key], (int, float)):
                    copy[key] = sc(float(copy[key]))
            out[pax_type] = copy
        return out
