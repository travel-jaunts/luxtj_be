"""Admin flight booking report queries."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_api.reports.flight_bookings.serializers import (
    ExtraServiceLineSerializer,
    FlightBookingDetailSerializer,
    FlightBookingListFilters,
    FlightBookingListItemSerializer,
    FlightBookingListResultSerializer,
    JourneySummarySerializer,
    PassengerDetailSerializer,
    PaymentTxnSerializer,
    PricingBlockSerializer,
    PricingLineSerializer,
    SegmentDetailSerializer,
)
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import (
    FlightBookingDetailsRow,
    FlightBookingItineraryDetailsRow,
    FlightBookingPassengerDetailsRow,
    FlightBookingTransactionDetailsRow,
)
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_models import (
    PaymentGatewayTransactionRow,
)

STATUS_ALL = "all"


def _as_utc_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _as_utc_end(d: date) -> datetime:
    return datetime.combine(d, time.max, tzinfo=timezone.utc)


def _money(value: Decimal | float | int | None) -> float:
    return float(value or 0)


def _pax_name(p: FlightBookingPassengerDetailsRow) -> str:
    parts = [p.title or "", p.first_name or "", p.last_name or ""]
    return " ".join(x for x in parts if x).strip() or "—"


def _payment_status_for(rows: list[PaymentGatewayTransactionRow]) -> str:
    statuses = [str(r.status or "").lower() for r in rows]
    if any(s == "accepted" for s in statuses):
        return "Paid"
    if any(s == "partially_refunded" for s in statuses):
        return "Partially Refunded"
    if any(s == "refunded" for s in statuses):
        return "Refunded"
    if any(s in {"pending", "initiated"} for s in statuses):
        return "Pending"
    if any(s in {"failed", "cancelled", "canceled", "declined"} for s in statuses):
        return "Failed"
    if rows:
        return str(rows[0].status or "Unknown").replace("_", " ").title()
    return "Unpaid"


def _build_journeys(
    segments: list[FlightBookingItineraryDetailsRow],
) -> list[JourneySummarySerializer]:
    by_rph: dict[int, list[FlightBookingItineraryDetailsRow]] = {}
    for seg in sorted(segments, key=lambda s: (s.rph or 1, s.departure_datetime or "")):
        by_rph.setdefault(int(seg.rph or 1), []).append(seg)
    out: list[JourneySummarySerializer] = []
    for rph in sorted(by_rph):
        segs = by_rph[rph]
        first, last = segs[0], segs[-1]
        out.append(
            JourneySummarySerializer(
                airline_code=first.airline_code,
                origin=first.origin,
                destination=last.destination,
                stops=max(0, len(segs) - 1),
                origin_label=first.origin,
                destination_label=last.destination,
            )
        )
    return out


def _route_summary(journeys: list[JourneySummarySerializer], booking: FlightBookingDetailsRow) -> str:
    if not journeys:
        o = booking.origin or "?"
        d = booking.destination or "?"
        return f"{o} → {d}"
    parts: list[str] = []
    for j in journeys:
        if not parts:
            parts.append(j.origin or "?")
        parts.append(j.destination or "?")
    # Deduplicate consecutive airports while preserving path
    cleaned: list[str] = []
    for p in parts:
        if not cleaned or cleaned[-1] != p:
            cleaned.append(p)
    return " → ".join(cleaned)


def _extract_extras(
    passengers: list[FlightBookingPassengerDetailsRow],
    currency: str | None,
) -> list[ExtraServiceLineSerializer]:
    lines: list[ExtraServiceLineSerializer] = []
    type_map = {
        "SeatDetails": "Seat",
        "BaggageDetails": "Extra baggage",
        "MealDetails": "Meal",
        "ServiceDetails": "Service",
    }
    for pax in passengers:
        attrs = pax.attributes if isinstance(pax.attributes, dict) else {}
        name = _pax_name(pax)
        for key, label in type_map.items():
            raw = attrs.get(key)
            items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                segment = (
                    str(item.get("segment") or item.get("Segment") or item.get("route") or "")
                    or None
                )
                detail = (
                    str(
                        item.get("description")
                        or item.get("Description")
                        or item.get("detail")
                        or item.get("code")
                        or item.get("Code")
                        or ""
                    )
                    or None
                )
                price_raw = item.get("price") or item.get("Price") or item.get("Amount")
                try:
                    price = float(price_raw) if price_raw is not None else None
                except (TypeError, ValueError):
                    price = None
                lines.append(
                    ExtraServiceLineSerializer(
                        passenger_name=name,
                        age_type=pax.age_type or "Adult",
                        item_type=label,
                        segment=segment,
                        detail=detail,
                        price=price,
                        currency=currency,
                    )
                )
    return lines


class FlightBookingReportsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_filters(self, filters: FlightBookingListFilters) -> list[Any]:
        clauses: list[Any] = []
        status = (filters.status or STATUS_ALL).strip()
        if status and status.lower() != STATUS_ALL:
            clauses.append(FlightBookingDetailsRow.status == status)

        email = (filters.email or "").strip()
        if email:
            clauses.append(FlightBookingDetailsRow.email.ilike(f"%{email}%"))

        booking_no = (filters.booking_no or "").strip()
        if booking_no:
            like = f"%{booking_no}%"
            clauses.append(
                or_(
                    FlightBookingDetailsRow.app_reference.ilike(like),
                    FlightBookingDetailsRow.gdspnr.ilike(like),
                    FlightBookingDetailsRow.booking_id.ilike(like),
                )
            )

        airline = (filters.airline or "").strip().upper()
        if airline:
            itin_exists = (
                select(FlightBookingItineraryDetailsRow.id)
                .where(
                    FlightBookingItineraryDetailsRow.app_reference
                    == FlightBookingDetailsRow.app_reference,
                    FlightBookingItineraryDetailsRow.airline_code == airline,
                )
                .exists()
            )
            clauses.append(itin_exists)

        if filters.from_date is not None:
            clauses.append(FlightBookingDetailsRow.created_at >= _as_utc_start(filters.from_date))
        if filters.to_date is not None:
            clauses.append(FlightBookingDetailsRow.created_at <= _as_utc_end(filters.to_date))
        return clauses

    def _filtered_select(self, filters: FlightBookingListFilters) -> Select[Any]:
        stmt = select(FlightBookingDetailsRow)
        for clause in self._base_filters(filters):
            stmt = stmt.where(clause)
        return stmt

    async def list_bookings(
        self, filters: FlightBookingListFilters
    ) -> FlightBookingListResultSerializer:
        base = self._filtered_select(filters)
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        page = filters.page
        page_size = filters.page_size
        offset = (page - 1) * page_size
        rows = list(
            (
                await self._session.execute(
                    base.order_by(FlightBookingDetailsRow.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        items = await self._hydrate_list_items(rows)
        return FlightBookingListResultSerializer(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def _hydrate_list_items(
        self, rows: list[FlightBookingDetailsRow]
    ) -> list[FlightBookingListItemSerializer]:
        if not rows:
            return []
        refs = [r.app_reference for r in rows]

        txn_rows = list(
            (
                await self._session.execute(
                    select(FlightBookingTransactionDetailsRow).where(
                        FlightBookingTransactionDetailsRow.app_reference.in_(refs)
                    )
                )
            )
            .scalars()
            .all()
        )
        txn_by_ref = {t.app_reference: t for t in txn_rows}

        pax_rows = list(
            (
                await self._session.execute(
                    select(FlightBookingPassengerDetailsRow).where(
                        FlightBookingPassengerDetailsRow.app_reference.in_(refs)
                    )
                )
            )
            .scalars()
            .all()
        )
        pax_by_ref: dict[str, list[FlightBookingPassengerDetailsRow]] = {}
        for p in pax_rows:
            pax_by_ref.setdefault(p.app_reference, []).append(p)

        itin_rows = list(
            (
                await self._session.execute(
                    select(FlightBookingItineraryDetailsRow).where(
                        FlightBookingItineraryDetailsRow.app_reference.in_(refs)
                    )
                )
            )
            .scalars()
            .all()
        )
        itin_by_ref: dict[str, list[FlightBookingItineraryDetailsRow]] = {}
        for s in itin_rows:
            itin_by_ref.setdefault(s.app_reference, []).append(s)

        pay_rows = list(
            (
                await self._session.execute(
                    select(PaymentGatewayTransactionRow).where(
                        PaymentGatewayTransactionRow.app_reference.in_(refs)
                    )
                )
            )
            .scalars()
            .all()
        )
        pay_by_ref: dict[str, list[PaymentGatewayTransactionRow]] = {}
        for pay in pay_rows:
            pay_by_ref.setdefault(pay.app_reference, []).append(pay)

        items: list[FlightBookingListItemSerializer] = []
        for booking in rows:
            ref = booking.app_reference
            txn = txn_by_ref.get(ref)
            pax = pax_by_ref.get(ref, [])
            lead = pax[0] if pax else None
            items.append(
                FlightBookingListItemSerializer(
                    app_reference=ref,
                    status=booking.status,
                    payment_status=_payment_status_for(pay_by_ref.get(ref, [])),
                    booking_source=booking.booking_source,
                    gdspnr=booking.gdspnr,
                    booking_id=booking.booking_id,
                    trip_type=booking.trip_type,
                    cabin_class=booking.cabin_class,
                    origin=booking.origin,
                    destination=booking.destination,
                    departure_date=str(booking.departure_date) if booking.departure_date else None,
                    return_date=str(booking.return_date) if booking.return_date else None,
                    email=booking.email,
                    phone=booking.phone,
                    lead_passenger_name=_pax_name(lead) if lead else None,
                    passenger_count=len(pax),
                    journeys=_build_journeys(itin_by_ref.get(ref, [])),
                    total_fare=_money(txn.total_fare) if txn else None,
                    currency=txn.currency if txn else None,
                    payment_mode=txn.payment_mode if txn else None,
                    created_at=booking.created_at,
                )
            )
        return items

    async def get_details(self, app_reference: str) -> FlightBookingDetailSerializer | None:
        ref = app_reference.strip()
        booking = (
            await self._session.execute(
                select(FlightBookingDetailsRow).where(
                    FlightBookingDetailsRow.app_reference == ref
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return None

        txn = (
            await self._session.execute(
                select(FlightBookingTransactionDetailsRow).where(
                    FlightBookingTransactionDetailsRow.app_reference == ref
                )
            )
        ).scalar_one_or_none()

        passengers = list(
            (
                await self._session.execute(
                    select(FlightBookingPassengerDetailsRow)
                    .where(FlightBookingPassengerDetailsRow.app_reference == ref)
                    .order_by(FlightBookingPassengerDetailsRow.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        segments = list(
            (
                await self._session.execute(
                    select(FlightBookingItineraryDetailsRow)
                    .where(FlightBookingItineraryDetailsRow.app_reference == ref)
                    .order_by(
                        FlightBookingItineraryDetailsRow.rph.asc(),
                        FlightBookingItineraryDetailsRow.departure_datetime.asc(),
                    )
                )
            )
            .scalars()
            .all()
        )
        payments = list(
            (
                await self._session.execute(
                    select(PaymentGatewayTransactionRow)
                    .where(PaymentGatewayTransactionRow.app_reference == ref)
                    .order_by(PaymentGatewayTransactionRow.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        journeys = _build_journeys(segments)
        admin_currency = (txn.currency if txn else None) or "USD"
        rate = float(txn.currency_conversion_rate) if txn and txn.currency_conversion_rate else None
        # Prefer PG booked currency when conversion was applied at payment time.
        booked_currency: str | None = None
        pg_rate: float | None = None
        for pay in payments:
            if pay.pg_currency:
                booked_currency = pay.pg_currency
            if pay.pg_currency_conversion_rate is not None:
                pg_rate = float(pay.pg_currency_conversion_rate)
                break
        conversion_rate = pg_rate if pg_rate is not None else (rate if rate and rate != 1 else None)

        pricing: PricingBlockSerializer | None = None
        if txn is not None:

            def to_booked(admin_amt: float) -> float | None:
                if not (conversion_rate and conversion_rate > 0 and booked_currency):
                    return None
                # Prefer treating stored PG rate as booked_amount = admin * rate when rate >= 1,
                # else admin / rate (common when rate is admin-per-booked unit).
                if conversion_rate >= 1:
                    return round(admin_amt * conversion_rate, 4)
                return round(admin_amt / conversion_rate, 4)

            def line(label: str, amount: float) -> PricingLineSerializer:
                return PricingLineSerializer(
                    label=label,
                    admin_amount=amount,
                    booked_amount=to_booked(amount),
                )

            lines = [
                line("Basic fare", _money(txn.basic_fare)),
                line("Taxes and fees", _money(txn.airline_tax)),
                line("Admin markup", _money(txn.admin_markup)),
                line("Admin discount", _money(txn.admin_discount)),
                line("Promo discount", _money(txn.discount_amount)),
                line("Convenience fee", _money(txn.convenience_fee)),
            ]

            baggage_total = None
            attrs = booking.attributes if isinstance(booking.attributes, dict) else {}
            quote = attrs.get("pricing_quote") if isinstance(attrs.get("pricing_quote"), dict) else {}
            if quote.get("baggage_selection_total") is not None:
                try:
                    baggage_total = float(quote["baggage_selection_total"])
                except (TypeError, ValueError):
                    baggage_total = None

            total_admin = _money(txn.total_fare)
            # Prefer gateway charged amount in booked currency when present.
            total_booked = None
            for pay in payments:
                if pay.pg_amount is not None and pay.pg_currency:
                    total_booked = _money(pay.pg_amount)
                    booked_currency = pay.pg_currency or booked_currency
                    break
            if total_booked is None:
                total_booked = to_booked(total_admin)

            pricing = PricingBlockSerializer(
                admin_currency=admin_currency,
                booked_currency=booked_currency,
                conversion_rate=conversion_rate,
                lines=lines,
                total_fare_admin=total_admin,
                total_fare_booked=total_booked,
                excess_baggage_total=baggage_total,
            )

        lead = passengers[0] if passengers else None
        return FlightBookingDetailSerializer(
            app_reference=booking.app_reference,
            status=booking.status,
            payment_status=_payment_status_for(payments),
            booking_source=booking.booking_source,
            booking_id=booking.booking_id,
            book_guid=booking.book_guid,
            gdspnr=booking.gdspnr,
            trip_type=booking.trip_type,
            cabin_class=booking.cabin_class,
            origin=booking.origin,
            destination=booking.destination,
            departure_date=str(booking.departure_date) if booking.departure_date else None,
            return_date=str(booking.return_date) if booking.return_date else None,
            email=booking.email,
            phone=booking.phone,
            lead_passenger_name=_pax_name(lead) if lead else None,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            route_summary=_route_summary(journeys, booking),
            passengers=[
                PassengerDetailSerializer(
                    title=p.title,
                    first_name=p.first_name,
                    last_name=p.last_name,
                    age_type=p.age_type,
                    date_of_birth=p.date_of_birth,
                    gender=p.gender,
                    nationality=p.nationality,
                    document_number=p.document_number,
                    document_expiry=p.document_expiry,
                    ticket_number=p.ticket_number,
                    attributes=p.attributes if isinstance(p.attributes, dict) else None,
                )
                for p in passengers
            ],
            segments=[
                SegmentDetailSerializer(
                    airline_code=s.airline_code,
                    flight_number=s.flight_number,
                    origin=s.origin,
                    destination=s.destination,
                    departure_datetime=s.departure_datetime,
                    arrival_datetime=s.arrival_datetime,
                    cabin_class=s.cabin_class,
                    pnr=s.pnr,
                    rph=int(s.rph or 1),
                )
                for s in segments
            ],
            journeys=journeys,
            extras=_extract_extras(passengers, admin_currency),
            pricing=pricing,
            payments=[
                PaymentTxnSerializer(
                    gateway=pay.pg_code,
                    status=pay.status,
                    amount=_money(pay.amount),
                    currency=pay.currency,
                    pg_amount=_money(pay.pg_amount) if pay.pg_amount is not None else None,
                    pg_currency=pay.pg_currency,
                    reference=pay.pg_reference_id,
                    transaction_id=pay.transaction_id,
                )
                for pay in payments
            ],
            attributes=booking.attributes if isinstance(booking.attributes, dict) else None,
            details_snapshot=(
                booking.details_snapshot if isinstance(booking.details_snapshot, dict) else None
            ),
        )

    async def export_csv(self, filters: FlightBookingListFilters) -> str:
        """Export filtered bookings (capped) as CSV text."""
        export_filters = filters.model_copy(update={"page": 1, "page_size": 100})
        # Pull up to 5 pages (500 rows) for admin export without streaming infra.
        all_items: list[FlightBookingListItemSerializer] = []
        for page in range(1, 6):
            page_filters = export_filters.model_copy(update={"page": page})
            result = await self.list_bookings(page_filters)
            all_items.extend(result.items)
            if page * export_filters.page_size >= result.total:
                break

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "app_reference",
                "status",
                "payment_status",
                "booking_source",
                "gdspnr",
                "email",
                "phone",
                "lead_passenger",
                "passenger_count",
                "trip_type",
                "cabin_class",
                "origin",
                "destination",
                "departure_date",
                "total_fare",
                "currency",
                "payment_mode",
                "created_at",
            ]
        )
        for item in all_items:
            writer.writerow(
                [
                    item.app_reference,
                    item.status,
                    item.payment_status,
                    item.booking_source,
                    item.gdspnr or "",
                    item.email or "",
                    item.phone or "",
                    item.lead_passenger_name or "",
                    item.passenger_count,
                    item.trip_type,
                    item.cabin_class or "",
                    item.origin or "",
                    item.destination or "",
                    item.departure_date or "",
                    item.total_fare if item.total_fare is not None else "",
                    item.currency or "",
                    item.payment_mode or "",
                    item.created_at.isoformat() if item.created_at else "",
                ]
            )
        return buf.getvalue()
