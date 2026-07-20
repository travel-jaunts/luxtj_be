"""General helper and formatting utilities for the recommendation engine."""

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from .models import BucketListRecommendationResult, UnavailableResult


class EnhancedJSONEncoder(json.JSONEncoder):
    """Encode dataclasses, dates, datetimes, and enum-like values."""

    def default(self, obj: Any) -> Any:
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, datetime | date):
            return obj.isoformat()
        if hasattr(obj, "value"):
            return obj.value
        return super().default(obj)


def to_json(obj: Any, indent: int = 2) -> str:
    """Serialize engine models and dataclasses into JSON."""
    return json.dumps(obj, cls=EnhancedJSONEncoder, indent=indent)


def format_recommendation_output(output: BucketListRecommendationResult) -> str:
    """Render a human-readable recommendation report for logging and inspection."""
    lines = [
        "=" * 70,
        " BUCKET LIST RECOMMENDATION REPORT",
        f" Generated at: {output.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
    ]

    for window in output.windows:
        lines.append(
            f"\nWindow: {window.window_name} "
            f"({window.departure_start} to {window.departure_end})"
        )
        lines.append("-" * 70)

        tier_items = (
            ("Lite", window.lite),
            ("Plus", window.plus),
            ("Ultra", window.ultra),
        )
        for tier_name, item in tier_items:
            lines.append(f"  TIER: {tier_name.upper()}")
            if isinstance(item, UnavailableResult):
                lines.append(f"    [UNAVAILABLE] Reasons: {item.reason_codes}")
                lines.append(f"    Explanation: {item.explanation}")
            else:
                lines.append(
                    f"    [AVAILABLE] ID: {item.recommendation_id} | "
                    f"Score: {item.score:.2f} | "
                    f"Total Price: ${item.package_pricing:.2f}"
                )
                outbound = item.flights.outbound
                lines.append(
                    f"      Outbound Flight: {outbound.carrier} "
                    f"{outbound.flight_number} "
                    f"({outbound.origin} -> {outbound.destination}) "
                    f"on {outbound.departure_date} (${outbound.price:.2f})"
                )
                lines.append("      Hotel Stays:")
                for selection in item.hotels:
                    hotel = selection.hotel_deal
                    lines.append(
                        f"        - {selection.destination.name}: {hotel.name} "
                        f"({hotel.tier.value}) | In: {hotel.check_in} "
                        f"Out: {hotel.check_out} | {selection.destination.days} nights | "
                        f"${hotel.price_per_night:.2f}/night "
                        f"(Total: ${hotel.total_price:.2f})"
                    )

                return_flight = item.flights.return_flight
                lines.append(
                    f"      Return Flight: {return_flight.carrier} "
                    f"{return_flight.flight_number} "
                    f"({return_flight.origin} -> {return_flight.destination}) "
                    f"on {return_flight.departure_date} "
                    f"(${return_flight.price:.2f})"
                )
                lines.append(f"      Explanation: {item.explanation}")
            lines.append("  " + "." * 60)

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)
