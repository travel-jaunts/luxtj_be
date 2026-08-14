"""Flight promo evaluation — mirrors TeenvaFlightPromo (uses marketing_offers)."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.marketing.domain.enums import OfferStatusEnum, OfferTypeEnum
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_models import MarketingOfferRow
from luxtj.utils import timeutils

REASON_EMPTY = "empty_code"
REASON_NOT_FOUND = "not_found"
REASON_INACTIVE = "inactive"
REASON_EXPIRED = "expired"
REASON_BELOW_MINIMUM = "below_minimum"
REASON_INVALID_CONFIG = "invalid_config"

AMOUNT_DECIMALS = 4
PERCENT_DECIMALS = 2


class FlightPromo:
    @staticmethod
    def _failure(reason: str, message: str) -> dict[str, Any]:
        return {
            "applicable": False,
            "message": message,
            "reason": reason,
            "promo_code": None,
            "promo_description": None,
            "discount_type": None,
            "discount_rule_value": 0.0,
            "discount_amount_admin": 0.0,
        }

    @staticmethod
    def _applies_to_module(row: MarketingOfferRow, module: str) -> bool:
        apps = row.applicability_on if isinstance(row.applicability_on, list) else []
        if not apps:
            return False
        return any(str(a).upper() in (module.upper(), "ALL", "*") for a in apps)

    @staticmethod
    async def resolve_flight_offer(
        session: AsyncSession, promo_code: str
    ) -> MarketingOfferRow | None:
        code = promo_code.strip().upper()
        rows = list(
            (
                await session.execute(
                    select(MarketingOfferRow).where(func.upper(MarketingOfferRow.code) == code)
                )
            )
            .scalars()
            .all()
        )
        matches = [
            row
            for row in rows
            if str(row.status) != OfferStatusEnum.DELETED.value
            and FlightPromo._applies_to_module(row, "FLIGHT")
        ]
        if not matches:
            return None
        active = [r for r in matches if str(r.status) == OfferStatusEnum.ACTIVE.value]
        return active[0] if active else matches[0]

    @staticmethod
    def compute_discount_amount(offer: MarketingOfferRow, base_amount_admin: float) -> float:
        amt = float(offer.discount_value or 0)
        if amt <= 0:
            return 0.0
        otype = str(offer.type or "").lower()
        if otype in (OfferTypeEnum.PERCENTAGE_OFF.value, "percentage", "percentage_off"):
            return min(
                base_amount_admin,
                round((amt * base_amount_admin) / 100, AMOUNT_DECIMALS),
            )
        return min(base_amount_admin, round(amt, AMOUNT_DECIMALS))

    @staticmethod
    async def evaluate(
        session: AsyncSession, promo_code: str, gross_fare_admin: float
    ) -> dict[str, Any]:
        trim = promo_code.strip()
        if not trim:
            return FlightPromo._failure(REASON_EMPTY, "Promo code is required.")
        offer = await FlightPromo.resolve_flight_offer(session, trim)
        if offer is None:
            return FlightPromo._failure(REASON_NOT_FOUND, "This promo code is not valid.")
        if str(offer.status) != OfferStatusEnum.ACTIVE.value:
            return FlightPromo._failure(REASON_INACTIVE, "This promo code is not active.")
        now = timeutils.datetime_now()
        end = offer.validity_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        if end < now:
            return FlightPromo._failure(REASON_EXPIRED, "This promo code has expired.")
        start = offer.validity_start
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if start > now:
            return FlightPromo._failure(REASON_INACTIVE, "This promo code is not active yet.")
        minimum = float(offer.min_booking_value or 0)
        if minimum > 0 and gross_fare_admin < minimum:
            return FlightPromo._failure(
                REASON_BELOW_MINIMUM,
                "This promo code requires a minimum fare that is not met for this booking.",
            )
        discount = FlightPromo.compute_discount_amount(offer, gross_fare_admin)
        if discount <= 0:
            return FlightPromo._failure(
                REASON_INVALID_CONFIG,
                "This promo code cannot be applied to this fare.",
            )
        otype = str(offer.type or "").lower()
        discount_type = (
            "percentage"
            if otype in (OfferTypeEnum.PERCENTAGE_OFF.value, "percentage", "percentage_off")
            else "plus"
        )
        rule_value = float(offer.discount_value or 0)
        return {
            "applicable": True,
            "message": "Applied successfully",
            "reason": None,
            "promo_code": trim.upper(),
            "promo_description": str(offer.name or ""),
            "discount_type": discount_type,
            "discount_rule_value": round(
                rule_value, PERCENT_DECIMALS if discount_type == "percentage" else AMOUNT_DECIMALS
            ),
            "discount_amount_admin": round(discount, AMOUNT_DECIMALS),
        }
