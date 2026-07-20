from datetime import date, timedelta

from .config import EngineConfig
from .enums import CalendarEventType, HolidayType
from .models import CalendarEventInput, CalendarPeriodInput, TravelWindow


def next_annual_occurrence(
    stored_date: date,
    reference_date: date,
    *,
    leap_day_fallback_day: int = 28,
) -> date:
    """Return the next annual occurrence on or after the reference date."""

    def occurrence(year: int) -> date:
        try:
            return date(year, stored_date.month, stored_date.day)
        except ValueError:
            if stored_date.month == 2 and stored_date.day == 29:
                return date(year, 2, leap_day_fallback_day)
            raise

    candidate = occurrence(reference_date.year)
    if candidate < reference_date:
        candidate = occurrence(reference_date.year + 1)
    return candidate


def target_date_for_event(
    event: CalendarEventInput,
    reference_date: date,
    config: EngineConfig,
) -> date | None:
    if event.event_type in {
        CalendarEventType.BIRTHDAY,
        CalendarEventType.ANNIVERSARY,
    }:
        return next_annual_occurrence(
            event.event_date,
            reference_date,
            leap_day_fallback_day=config.leap_day_fallback_day,
        )
    if event.event_date < reference_date:
        return None
    return event.event_date


def _previous_weekday(anchor: date, weekday: int) -> date:
    days_back = (anchor.weekday() - weekday) % 7
    if days_back == 0:
        days_back = 7
    return anchor - timedelta(days=days_back)


def _next_weekday(anchor: date, weekday: int) -> date:
    days_forward = (weekday - anchor.weekday()) % 7
    if days_forward == 0:
        days_forward = 7
    return anchor + timedelta(days=days_forward)


def generate_event_windows(
    target_date: date,
    reference_date: date,
    config: EngineConfig,
) -> tuple[TravelWindow, ...]:
    """Generate deterministic celebration windows with the event inside the trip."""

    previous_saturday = _previous_weekday(target_date, 5)
    previous_friday = _previous_weekday(target_date, 4)
    next_friday = _next_weekday(target_date, 4)
    next_sunday = _next_weekday(target_date, 6)
    raw = (
        ("Previous weekend through occasion", previous_saturday, target_date + timedelta(days=1)),
        ("Occasion week escape", target_date - timedelta(days=1), next_friday),
        ("Extended weekend bridge", previous_friday, target_date + timedelta(days=2)),
        ("Full celebration week", previous_saturday, next_sunday),
        (
            "Balanced midweek celebration",
            target_date - timedelta(days=2),
            target_date + timedelta(days=2),
        ),
    )

    windows: list[TravelWindow] = []
    seen: set[tuple[date, date]] = set()
    for name, start_date, end_date in raw:
        if start_date < reference_date:
            continue
        if not start_date < target_date < end_date:
            continue
        key = (start_date, end_date)
        if key in seen:
            continue
        seen.add(key)
        windows.append(
            TravelWindow(
                name=name,
                start_date=start_date,
                end_date=end_date,
                target_date=target_date,
            )
        )
    windows.sort(key=lambda item: (item.start_date, item.end_date, item.name))
    return tuple(windows[: config.max_windows_per_opportunity])


def is_family_period(period: CalendarPeriodInput) -> bool:
    if HolidayType.FAMILY_LUXURY_HOLIDAYS in period.holiday_types:
        return True
    normalized_name = period.period_name.casefold()
    family_terms = (
        "children",
        "child",
        "kids",
        "school",
        "family",
        "summer break",
        "winter break",
    )
    return any(term in normalized_name for term in family_terms)


def generate_period_windows(
    period: CalendarPeriodInput,
    reference_date: date,
    config: EngineConfig,
) -> tuple[TravelWindow, ...]:
    buffer_days = config.flexible_period_buffer_days if period.is_date_flexible else 0
    allowed_start = max(period.period_start - timedelta(days=buffer_days), reference_date)
    allowed_end = period.period_end + timedelta(days=buffer_days)
    if allowed_end <= allowed_start:
        return ()

    durations = (
        config.family_period_nights if is_family_period(period) else config.standard_period_nights
    )
    windows: list[TravelWindow] = []
    seen: set[tuple[date, date]] = set()
    total_days = (allowed_end - allowed_start).days
    for nights in durations:
        if nights > total_days:
            continue
        latest_start = allowed_end - timedelta(days=nights)
        midpoint_start = allowed_start + timedelta(days=max((total_days - nights) // 2, 0))
        starts = (allowed_start, midpoint_start, latest_start)
        for index, start_date in enumerate(starts):
            end_date = start_date + timedelta(days=nights)
            if start_date < allowed_start or end_date > allowed_end:
                continue
            key = (start_date, end_date)
            if key in seen:
                continue
            seen.add(key)
            position = ("opening", "mid-period", "closing")[index]
            windows.append(
                TravelWindow(
                    name=f"{nights}-night {position} option",
                    start_date=start_date,
                    end_date=end_date,
                )
            )

    windows.sort(key=lambda item: (item.start_date, item.nights, item.name))
    return tuple(windows[: config.max_windows_per_opportunity])
