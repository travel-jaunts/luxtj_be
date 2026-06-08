from datetime import date, timedelta

from luxtj.utils import timeutils


def weekly_range(
    *, from_date: date | None, to_date: date | None, fallback_weeks: int = 12
) -> list[date]:
    """Generate start date of each week (Monday) between from_date and to_date."""
    end_date = to_date or timeutils.datetime_now().date()
    start_date = from_date or (end_date - timedelta(days=7 * (fallback_weeks - 1)))
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    weeks: list[date] = []
    current = start_date - timedelta(days=start_date.weekday())

    while current <= end_date:
        weeks.append(current)
        current += timedelta(days=7)

    return weeks


def yearly_range(
    *, from_date: date | None, to_date: date | None, fallback_years: int = 3
) -> list[date]:
    """Generate first day of each year between from_date and to_date."""
    end_date = to_date or timeutils.datetime_now().date()
    start_date = from_date or (end_date - timedelta(days=365 * (fallback_years - 1)))
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    years: list[date] = []
    current_year = start_date.year
    final_year = end_date.year

    while current_year <= final_year:
        years.append(date(current_year, 1, 1))
        current_year += 1

    return years

