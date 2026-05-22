from datetime import UTC, datetime


def datetime_now() -> datetime:
    """Utility function to get the current datetime in UTC timezone."""
    return datetime.now(UTC)
