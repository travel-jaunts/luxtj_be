"""Hotel promo evaluation — mirrors TeenvaHotelPromo (uses marketing_offers)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
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


class HotelPromo:
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
    async def resolve_hotel_offer(
        session: AsyncSession, promo_code: str
    ) -> MarketingOfferRow | None:
        stmt = select(MarketingOfferRow).where(MarketingOfferRow.code == promo_code)
        offer = (await session.execute(stmt)).scalar_one_or_none()
        if offer is None:
            return None
        # Prefer hotel-applicable offers when applicability_on is set
        apps = offer.applicability_on if isinstance(offer.applicability_on, list) else []
        if apps and not any(str(a).upper() in ("HOTEL", "ALL", "*") for a in apps):
            return None
        return offer

    @staticmethod
    def compute_discount_amount(offer: MarketingOfferRow, base_amount_admin: float) -> float:
        amt = float(offer.discount_value or 0)
        if amt <= 0:
            return 0.0
        otype = str(offer.type or "").lower()
        if otype in (OfferTypeEnum.PERCENTAGE_OFF.value, "percentage", "percentage_off"):
            return min(base_amount_admin, round((amt * base_amount_admin) / 100, 2))
        return min(base_amount_admin, round(amt, 2))

    @staticmethod
    async def evaluate(
        session: AsyncSession, promo_code: str, payable_total_admin: float
    ) -> dict[str, Any]:
        trim = promo_code.strip()
        if not trim:
            return HotelPromo._failure(REASON_EMPTY, "Promo code is required.")
        offer = await HotelPromo.resolve_hotel_offer(session, trim)
        if offer is None:
            return HotelPromo._failure(REASON_NOT_FOUND, "This promo code is not valid.")
        if str(offer.status) != OfferStatusEnum.ACTIVE.value:
            return HotelPromo._failure(REASON_INACTIVE, "This promo code is not active.")
        now = timeutils.datetime_now()
        end = offer.validity_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end < now:
            return HotelPromo._failure(REASON_EXPIRED, "This promo code has expired.")
        minimum = float(offer.min_booking_value or 0)
        if minimum > 0 and payable_total_admin < minimum:
            return HotelPromo._failure(
                REASON_BELOW_MINIMUM,
                "This promo code requires a minimum spend that is not met for this booking.",
            )
        discount = HotelPromo.compute_discount_amount(offer, payable_total_admin)
        if discount <= 0:
            return HotelPromo._failure(
                REASON_INVALID_CONFIG,
                "This promo code cannot be applied to this booking.",
            )
        otype = str(offer.type or "").lower()
        discount_type = (
            "percentage"
            if otype in (OfferTypeEnum.PERCENTAGE_OFF.value, "percentage", "percentage_off")
            else "plus"
        )
        return {
            "applicable": True,
            "message": "Applied successfully",
            "reason": None,
            "promo_code": trim,
            "promo_description": str(offer.name or ""),
            "discount_type": discount_type,
            "discount_rule_value": round(float(offer.discount_value or 0), 2),
            "discount_amount_admin": round(discount, 2),
        }
