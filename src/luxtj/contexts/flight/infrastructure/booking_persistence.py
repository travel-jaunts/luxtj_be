"""Persist flight PreBook draft rows (admin currency)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.currency.domain.admin_currency import AdminCurrency
from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import (
    FlightBookingDetailsRow,
    FlightBookingItineraryDetailsRow,
    FlightBookingPassengerDetailsRow,
    FlightBookingTransactionDetailsRow,
)
from luxtj.utils import timeutils


def _seg_origin(seg: dict[str, Any]) -> dict[str, Any]:
    return seg.get("Origin") if isinstance(seg.get("Origin"), dict) else {}


def _seg_dest(seg: dict[str, Any]) -> dict[str, Any]:
    return seg.get("Destination") if isinstance(seg.get("Destination"), dict) else {}


def _combine_local(when: dict[str, Any]) -> str | None:
    d = str(when.get("date") or "").strip()
    t = str(when.get("time") or "").strip()
    if d and t:
        return f"{d} {t}"
    return d or t or None


def resolve_trip_type(flight_details: list[Any]) -> str:
    journeys = [j for j in flight_details if isinstance(j, list) and j]
    if len(journeys) <= 1:
        return "oneway"
    first = journeys[0][0] if isinstance(journeys[0][0], dict) else {}
    last_j = journeys[-1]
    last = last_j[-1] if isinstance(last_j[-1], dict) else first
    o1 = str(_seg_origin(first).get("AirportCode") or "").upper()
    d1 = str(_seg_dest(first).get("AirportCode") or "").upper()
    o2 = str(_seg_origin(last).get("AirportCode") or "").upper()
    d2 = str(_seg_dest(last).get("AirportCode") or "").upper()
    if len(journeys) == 2 and o1 == d2 and d1 == o2:
        return "return"
    return "multicity"


def _parse_date(raw: str | None) -> date | None:
    text = str(raw or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


async def persist_pre_book(
    session: AsyncSession,
    *,
    app_reference: str,
    booking_source: str,
    token_data: dict[str, Any],
    passengers: list[dict[str, Any]],
    charge_quote: dict[str, Any],
    payment_gateway_code: str | None,
    fare_quote_token: str | None = None,
    created_by_id: str | None = None,
) -> FlightBookingDetailsRow:
    """Create booking + itinerary + pax + transaction draft (no supplier book)."""
    now = timeutils.datetime_now()
    price = token_data.get("Price") if isinstance(token_data.get("Price"), dict) else {}
    details = token_data.get("FlightDetails") if isinstance(token_data.get("FlightDetails"), list) else []
    journeys = [j for j in details if isinstance(j, list) and j]
    first_seg = journeys[0][0] if journeys and isinstance(journeys[0][0], dict) else {}
    last_j = journeys[-1] if journeys else []
    last_seg = last_j[-1] if last_j and isinstance(last_j[-1], dict) else first_seg
    lead = passengers[0] if passengers else {}

    booking = FlightBookingDetailsRow(
        id=str(uuid.uuid4()),
        app_reference=app_reference,
        booking_source=booking_source,
        status="BOOKING_STARTED",
        trip_type=resolve_trip_type(details),
        cabin_class=str(first_seg.get("CabinClass") or "") or None,
        origin=str(_seg_origin(first_seg).get("AirportCode") or "") or None,
        destination=str(_seg_dest(last_seg).get("AirportCode") or "") or None,
        departure_date=_parse_date(str(_seg_origin(first_seg).get("date") or "")),
        return_date=(
            _parse_date(str(_seg_origin(last_seg).get("date") or ""))
            if resolve_trip_type(details) == "return"
            else None
        ),
        email=str(lead.get("Email") or lead.get("email") or "") or None,
        phone=str(lead.get("ContactNo") or lead.get("phone") or "") or None,
        attributes={
            "fare_quote_token": fare_quote_token,
            "prebook_result_token": token_data.get("ResultToken"),
            "pricing_quote": charge_quote,
            "prebook_passenger_extras": _extract_extras(passengers),
        },
        details_snapshot={
            "FlightDetails": details,
            "Price": price,
            "BaggageAllowance": token_data.get("BaggageAllowance"),
            "Attributes": token_data.get("Attributes"),
        },
        created_by_id=created_by_id,
        created_at=now,
        updated_at=now,
    )
    session.add(booking)

    for j_idx, journey in enumerate(journeys, start=1):
        for s_idx, seg in enumerate(journey, start=1):
            if not isinstance(seg, dict):
                continue
            origin = _seg_origin(seg)
            dest = _seg_dest(seg)
            session.add(
                FlightBookingItineraryDetailsRow(
                    id=str(uuid.uuid4()),
                    app_reference=app_reference,
                    rph=j_idx,
                    airline_code=str(
                        seg.get("MarketingAirlineCode") or seg.get("OperatingAirlineCode") or ""
                    )
                    or None,
                    flight_number=str(seg.get("FlightNumber") or "") or None,
                    origin=str(origin.get("AirportCode") or "") or None,
                    destination=str(dest.get("AirportCode") or "") or None,
                    departure_datetime=_combine_local(origin),
                    arrival_datetime=_combine_local(dest),
                    cabin_class=str(seg.get("CabinClass") or "") or None,
                    segment_json={
                        **seg,
                        "journey_indicator": j_idx,
                        "segment_indicator": s_idx,
                    },
                    created_at=now,
                    updated_at=now,
                )
            )

    for pax in passengers:
        if not isinstance(pax, dict):
            continue
        pax_type = str(pax.get("PaxType") or pax.get("PassengerType") or "Adult").strip() or "Adult"
        session.add(
            FlightBookingPassengerDetailsRow(
                id=str(uuid.uuid4()),
                app_reference=app_reference,
                age_type=pax_type,
                title=str(pax.get("Title") or pax.get("title") or "") or None,
                first_name=str(pax.get("FirstName") or pax.get("first_name") or ""),
                last_name=str(pax.get("LastName") or pax.get("last_name") or ""),
                middle_name=str(pax.get("MiddleName") or pax.get("middle_name") or "") or None,
                gender=FlightCommon.gender_code_from_title(pax),
                date_of_birth=str(pax.get("DateOfBirth") or pax.get("dob") or "") or None,
                nationality=str(pax.get("Nationality") or pax.get("nationality") or "")[:3] or None,
                document_number=str(
                    pax.get("PassportNumber")
                    or pax.get("DocumentNumber")
                    or pax.get("passport_number")
                    or ""
                )
                or None,
                document_expiry=str(
                    pax.get("PassportExpiry")
                    or pax.get("DocumentExpiry")
                    or pax.get("passport_expiry")
                    or ""
                )
                or None,
                attributes={
                    k: pax.get(k)
                    for k in ("SeatDetails", "BaggageDetails", "MealDetails", "ServiceDetails")
                    if pax.get(k)
                }
                or None,
                created_at=now,
                updated_at=now,
            )
        )

    pb = price.get("PriceBreakup") if isinstance(price.get("PriceBreakup"), dict) else {}
    session.add(
        FlightBookingTransactionDetailsRow(
            id=str(uuid.uuid4()),
            app_reference=app_reference,
            basic_fare=Decimal(str(pb.get("BasicFare") or 0)),
            airline_tax=Decimal(str(pb.get("Tax") or 0)),
            admin_markup=Decimal("0"),
            admin_discount=Decimal(str(charge_quote.get("admin_discount") or 0)),
            promocode=charge_quote.get("promocode_applied"),
            discount_amount=Decimal(str(charge_quote.get("promo_discount") or 0)),
            convenience_fee=Decimal(str(charge_quote.get("convenience_fee_amount") or 0)),
            total_fare=Decimal(str(charge_quote.get("final_total_fare") or 0)),
            currency=AdminCurrency.code()[:3],
            currency_conversion_rate=Decimal("1"),
            payment_mode=(payment_gateway_code or "").lower() or None,
            pax_wise_fare_breakdown=price.get("PassengerBreakup")
            if isinstance(price.get("PassengerBreakup"), dict)
            else None,
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    return booking


def _extract_extras(passengers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in passengers:
        if not isinstance(p, dict):
            continue
        row = {
            k: p.get(k)
            for k in ("SeatDetails", "BaggageDetails", "MealDetails", "ServiceDetails")
            if p.get(k)
        }
        if row:
            out.append(row)
    return out
