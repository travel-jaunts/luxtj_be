"""
Date logic for the Bucket List Recommendation Engine.
Handles departure window bounds generation, departure date sampling,
and hotel stay and return-flight date calculations.
"""

import calendar
from datetime import date, timedelta

from .config import WindowConfig
from .models import Destination, Itinerary


def get_month_bounds(reference_date: date, month_offset: int) -> tuple[date, date]:
    """Calculate the first and last eligible dates in an offset month."""
    total_months = reference_date.month - 1 + month_offset
    target_year = reference_date.year + total_months // 12
    target_month = total_months % 12 + 1

    first_day = date(target_year, target_month, 1)
    _, last_day_number = calendar.monthrange(target_year, target_month)
    last_day = date(target_year, target_month, last_day_number)
    start_date = max(reference_date, first_day) if month_offset == 0 else first_day
    return start_date, last_day


def get_window_bounds(
    reference_date: date,
    window_config: WindowConfig,
) -> tuple[date, date]:
    """Calculate the inclusive bounds for a recommendation window."""
    start_date, _ = get_month_bounds(reference_date, window_config.start_month_offset)
    _, end_date = get_month_bounds(reference_date, window_config.end_month_offset)

    if start_date > end_date:
        start_date = end_date

    return start_date, end_date


def sample_dates_in_range(start_date: date, end_date: date, limit: int) -> list[date]:
    """Sample unique, evenly distributed dates from an inclusive range."""
    if limit <= 0:
        return []

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        return []
    if limit == 1:
        return [start_date]
    if total_days <= limit:
        return [start_date + timedelta(days=index) for index in range(total_days)]

    sampled_dates = []
    for index in range(limit):
        day_offset = round(index * (total_days - 1) / (limit - 1))
        sampled_dates.append(start_date + timedelta(days=day_offset))

    return sorted(set(sampled_dates))


def calculate_hotel_stays(
    departure_date: date,
    itinerary: Itinerary,
) -> list[tuple[Destination, date, date]]:
    """Calculate sequential check-in and check-out dates for all destinations."""
    stays: list[tuple[Destination, date, date]] = []
    current_check_in = departure_date

    for destination in itinerary.destinations:
        current_check_out = current_check_in + timedelta(days=destination.days)
        stays.append((destination, current_check_in, current_check_out))
        current_check_in = current_check_out

    return stays


def calculate_return_date(departure_date: date, itinerary: Itinerary) -> date:
    """Calculate the return date from the itinerary's total nights."""
    return departure_date + timedelta(days=itinerary.total_nights)
