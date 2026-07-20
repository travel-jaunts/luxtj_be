from datetime import timedelta

from .config import EngineConfig
from .date_logic import (
    generate_event_windows,
    generate_period_windows,
    is_family_period,
    target_date_for_event,
)
from .enums import BirthdayFor, CalendarSourceType, HolidayType
from .models import PersonalCalendarRecommendationInput, TravelOpportunity


def build_travel_opportunities(
    context: PersonalCalendarRecommendationInput,
    config: EngineConfig,
) -> tuple[TravelOpportunity, ...]:
    opportunities: list[TravelOpportunity] = []

    for event in context.events:
        target_date = target_date_for_event(event, context.reference_date, config)
        if target_date is None:
            continue
        windows = generate_event_windows(target_date, context.reference_date, config)
        if not windows:
            continue
        requires_family = (
            event.birthday_for is BirthdayFor.CHILD_BIRTHDAY
            or HolidayType.FAMILY_LUXURY_HOLIDAYS in event.holiday_types
        )
        opportunities.append(
            TravelOpportunity(
                source_item_id=event.source_item_id,
                source_type=CalendarSourceType.EVENT,
                source_label=event.label,
                holiday_types=event.holiday_types,
                target_date=target_date,
                allowed_start=min(window.start_date for window in windows),
                allowed_end=max(window.end_date for window in windows),
                is_date_flexible=True,
                requires_family_suitability=requires_family,
                windows=windows,
            )
        )

    for period in context.periods:
        windows = generate_period_windows(period, context.reference_date, config)
        if not windows:
            continue
        buffer_days = config.flexible_period_buffer_days if period.is_date_flexible else 0
        allowed_start = max(
            period.period_start - timedelta(days=buffer_days),
            context.reference_date,
        )
        allowed_end = period.period_end + timedelta(days=buffer_days)
        opportunities.append(
            TravelOpportunity(
                source_item_id=period.source_item_id,
                source_type=CalendarSourceType.PERIOD,
                source_label=period.period_name,
                holiday_types=period.holiday_types,
                target_date=None,
                allowed_start=allowed_start,
                allowed_end=allowed_end,
                is_date_flexible=period.is_date_flexible,
                requires_family_suitability=is_family_period(period),
                windows=windows,
            )
        )

    opportunities.sort(
        key=lambda item: (
            min(window.start_date for window in item.windows),
            item.source_type.value,
            item.source_item_id,
        )
    )
    return tuple(opportunities)
