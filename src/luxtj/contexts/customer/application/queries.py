from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.enums import (
    CalendarSourceType,
    DealTier,
    PlanType,
    TravelerType,
)


@dataclass(frozen=True)
class GetBucketListQuery:
    account_id: UUID
    include_deleted: bool = False


@dataclass(frozen=True)
class RecommendBucketListDealsQuery:
    account_id: UUID
    origin: str
    reference_date: date


@dataclass(frozen=True)
class RecommendPersonalCalendarDealsQuery:
    account_id: UUID
    origin_city: str
    origin_country: str
    reference_date: date
    pricing_currency: str
    calendar_item_id: UUID | None = None
    calendar_item_type: CalendarSourceType | None = None
    plan_types: tuple[PlanType, ...] = (PlanType.HOTEL_FLIGHT,)
    tiers: tuple[DealTier, ...] = (
        DealTier.LITE,
        DealTier.PLUS,
        DealTier.ULTRA,
    )
    adults: int = 1
    children_ages: tuple[int, ...] = ()
    rooms: int = 1
    traveler_type: TravelerType = TravelerType.SOLO
    mobility_constraints: tuple[str, ...] = ()
    wheelchair_required: bool = False
    preferred_travel_pace: str | None = None
    target_budget: Decimal | None = None
    maximum_budget: Decimal | None = None
    passport_country: str | None = None
    residency_country: str | None = None
    interests: tuple[str, ...] = ()
    travel_intent: str | None = None
