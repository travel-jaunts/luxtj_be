"""Normalize raw external-provider payloads into engine business models."""

from datetime import date, datetime
from typing import Any

from ..models import CancellationPolicy, FlightDeal, HotelDeal, HotelTier


def parse_date(value: Any) -> date:
    """Parse a supported provider date value into ``datetime.date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        if "T" in value:
            return datetime.fromisoformat(value).date()
        return datetime.strptime(value.split()[0], "%Y-%m-%d").date()
    raise ValueError(f"Unable to parse date value: {value}")


def parse_bool(value: Any, *, field_name: str) -> bool:
    """Parse a provider boolean without treating every non-empty string as true."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError(f"Invalid boolean value for {field_name}: {value!r}")


def parse_cancellation_policy(value: Any) -> CancellationPolicy:
    """Parse a provider cancellation-policy value."""
    if isinstance(value, CancellationPolicy):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for policy in CancellationPolicy:
            if policy.value == normalized:
                return policy
    return CancellationPolicy.NON_REFUNDABLE


def normalize_flight_deal(raw: dict[str, Any]) -> FlightDeal:
    """Normalize one raw flight payload into a ``FlightDeal``."""
    try:
        flight_id = str(raw.get("flight_id") or raw.get("id") or "")
        origin = str(raw.get("origin") or raw.get("from") or "").strip().upper()
        destination = (
            str(raw.get("destination") or raw.get("to") or "").strip().upper()
        )
        departure_date = parse_date(raw.get("departure_date") or raw.get("date"))

        raw_price = raw.get("price")
        if raw_price is None:
            raw_price = raw.get("cost")
        if raw_price is None:
            raise ValueError("Flight price is required")
        price = float(raw_price)

        carrier = str(raw.get("carrier") or raw.get("airline") or "").strip()
        flight_number = str(
            raw.get("flight_number") or raw.get("number") or ""
        ).strip()
        is_outbound = parse_bool(
            raw.get("is_outbound", False),
            field_name="is_outbound",
        )
        is_return = parse_bool(
            raw.get("is_return", False),
            field_name="is_return",
        )
        stops = int(raw.get("stops", 0))
        duration_minutes = int(raw.get("duration_minutes", 0))
        cancellation_policy = parse_cancellation_policy(
            raw.get("cancellation_policy")
        )

        if not flight_id:
            raise ValueError("Missing flight identifier (id or flight_id)")
        if not origin or not destination:
            raise ValueError("Flight origin and destination are required")
        if price < 0:
            raise ValueError("Flight price cannot be negative")
        if stops < 0:
            raise ValueError("Flight stops cannot be negative")
        if duration_minutes < 0:
            raise ValueError("Flight duration cannot be negative")

        return FlightDeal(
            flight_id=flight_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            price=price,
            carrier=carrier,
            flight_number=flight_number,
            is_outbound=is_outbound,
            is_return=is_return,
            stops=stops,
            duration_minutes=duration_minutes,
            cancellation_policy=cancellation_policy,
            provider_metadata=raw.get("provider_metadata") or raw,
        )
    except Exception as exc:
        raise ValueError(f"Flight normalization failed: {exc}") from exc


def normalize_hotel_deal(raw: dict[str, Any]) -> HotelDeal:
    """Normalize one raw hotel payload into a ``HotelDeal``."""
    try:
        hotel_id = str(raw.get("hotel_id") or raw.get("id") or "")
        name = str(raw.get("name") or raw.get("hotel_name") or "").strip()
        destination = (
            str(raw.get("destination") or raw.get("city") or "").strip().upper()
        )

        raw_tier = raw.get("tier")
        if isinstance(raw_tier, HotelTier):
            tier = raw_tier
        elif isinstance(raw_tier, str):
            tier = HotelTier(raw_tier.strip().capitalize())
        else:
            raise ValueError(f"Invalid or missing hotel tier: {raw_tier}")

        check_in = parse_date(raw.get("check_in") or raw.get("start_date"))
        check_out = parse_date(raw.get("check_out") or raw.get("end_date"))

        raw_price = raw.get("price_per_night")
        if raw_price is None:
            raw_price = raw.get("rate")
        if raw_price is None:
            raise ValueError("Hotel price per night is required")
        price_per_night = float(raw_price)

        rating = raw.get("rating")
        rating_value = float(rating) if rating is not None else None
        reviews_count = int(raw.get("reviews_count", 0))
        cancellation_policy = parse_cancellation_policy(
            raw.get("cancellation_policy")
        )

        if not hotel_id:
            raise ValueError("Missing hotel identifier (id or hotel_id)")
        if not name:
            raise ValueError("Hotel name is required")
        if not destination:
            raise ValueError("Hotel destination is required")
        if check_in >= check_out:
            raise ValueError(
                f"Check-in date ({check_in}) must be before check-out date ({check_out})"
            )
        if price_per_night < 0:
            raise ValueError("Hotel night price cannot be negative")
        if reviews_count < 0:
            raise ValueError("Reviews count cannot be negative")

        return HotelDeal(
            hotel_id=hotel_id,
            name=name,
            destination=destination,
            tier=tier,
            check_in=check_in,
            check_out=check_out,
            price_per_night=price_per_night,
            rating=rating_value,
            reviews_count=reviews_count,
            cancellation_policy=cancellation_policy,
            provider_metadata=raw.get("provider_metadata") or raw,
        )
    except Exception as exc:
        raise ValueError(f"Hotel normalization failed: {exc}") from exc
