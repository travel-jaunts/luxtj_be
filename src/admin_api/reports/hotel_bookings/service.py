"""Admin hotel booking report queries."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_api.reports.hotel_bookings.serializers import (
    GuestDetailSerializer,
    HotelBookingDetailSerializer,
    HotelBookingListFilters,
    HotelBookingListItemSerializer,
    HotelBookingListResultSerializer,
    PaymentTxnSerializer,
    PricingBlockSerializer,
    PricingLineSerializer,
    RoomDetailSerializer,
)
from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
    HotelCrsHotelImageRow,
    HotelCrsHotelRow,
    HotelCrsSupplierHotelMapRow,
)
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
    HotelBookingDetailsRow,
    HotelBookingItineraryDetailsRow,
    HotelBookingPaxDetailsRow,
    HotelBookingTransactionDetailsRow,
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


def _guest_name(p: HotelBookingPaxDetailsRow) -> str:
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


def _room_summary(rooms: list[HotelBookingItineraryDetailsRow]) -> str | None:
    names = [str(r.room_type_name or "").strip() for r in rooms if r.room_type_name]
    names = [n for n in names if n]
    if not names:
        return None
    return ", ".join(names)


def _crs_address(hotel: HotelCrsHotelRow) -> str | None:
    parts = [
        str(hotel.address_line1 or "").strip(),
        str(hotel.address_line2 or "").strip(),
        str(hotel.postal_code or "").strip(),
        str(hotel.location or "").strip(),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined or None


class HotelBookingReportsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        crs_session: AsyncSession | None = None,
    ) -> None:
        self._session = session
        self._crs_session = crs_session

    def _base_filters(self, filters: HotelBookingListFilters) -> list[Any]:
        clauses: list[Any] = [HotelBookingDetailsRow.deleted_at.is_(None)]
        status = (filters.status or STATUS_ALL).strip()
        if status and status.lower() != STATUS_ALL:
            clauses.append(HotelBookingDetailsRow.status == status)

        email = (filters.email or "").strip()
        if email:
            pax_exists = (
                select(HotelBookingPaxDetailsRow.id)
                .where(
                    HotelBookingPaxDetailsRow.app_reference
                    == HotelBookingDetailsRow.app_reference,
                    HotelBookingPaxDetailsRow.email.ilike(f"%{email}%"),
                )
                .exists()
            )
            clauses.append(pax_exists)

        booking_no = (filters.booking_no or "").strip()
        if booking_no:
            like = f"%{booking_no}%"
            clauses.append(
                or_(
                    HotelBookingDetailsRow.app_reference.ilike(like),
                    HotelBookingDetailsRow.booking_reference.ilike(like),
                    HotelBookingDetailsRow.confirmation_reference.ilike(like),
                )
            )

        hotel = (filters.hotel or "").strip()
        if hotel:
            like = f"%{hotel}%"
            clauses.append(
                or_(
                    HotelBookingDetailsRow.hotel_name.ilike(like),
                    HotelBookingDetailsRow.hotel_code.ilike(like),
                    HotelBookingDetailsRow.hotel_crs_hotel_code.ilike(like),
                    HotelBookingDetailsRow.hotel_location.ilike(like),
                )
            )

        if filters.from_date is not None:
            clauses.append(HotelBookingDetailsRow.created_at >= _as_utc_start(filters.from_date))
        if filters.to_date is not None:
            clauses.append(HotelBookingDetailsRow.created_at <= _as_utc_end(filters.to_date))
        return clauses

    def _filtered_select(self, filters: HotelBookingListFilters) -> Select[Any]:
        stmt = select(HotelBookingDetailsRow)
        for clause in self._base_filters(filters):
            stmt = stmt.where(clause)
        return stmt

    async def list_bookings(
        self, filters: HotelBookingListFilters
    ) -> HotelBookingListResultSerializer:
        base = self._filtered_select(filters)
        total = int(
            (
                await self._session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        page = filters.page
        page_size = filters.page_size
        offset = (page - 1) * page_size
        rows = list(
            (
                await self._session.execute(
                    base.order_by(HotelBookingDetailsRow.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        items = await self._hydrate_list_items(rows)
        return HotelBookingListResultSerializer(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def _hydrate_list_items(
        self, rows: list[HotelBookingDetailsRow]
    ) -> list[HotelBookingListItemSerializer]:
        if not rows:
            return []
        refs = [r.app_reference for r in rows]

        txn_rows = list(
            (
                await self._session.execute(
                    select(HotelBookingTransactionDetailsRow).where(
                        HotelBookingTransactionDetailsRow.app_reference.in_(refs)
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
                    select(HotelBookingPaxDetailsRow).where(
                        HotelBookingPaxDetailsRow.app_reference.in_(refs)
                    )
                )
            )
            .scalars()
            .all()
        )
        pax_by_ref: dict[str, list[HotelBookingPaxDetailsRow]] = {}
        for p in pax_rows:
            pax_by_ref.setdefault(p.app_reference, []).append(p)

        itin_rows = list(
            (
                await self._session.execute(
                    select(HotelBookingItineraryDetailsRow).where(
                        HotelBookingItineraryDetailsRow.app_reference.in_(refs)
                    )
                )
            )
            .scalars()
            .all()
        )
        itin_by_ref: dict[str, list[HotelBookingItineraryDetailsRow]] = {}
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

        items: list[HotelBookingListItemSerializer] = []
        for booking in rows:
            ref = booking.app_reference
            txn = txn_by_ref.get(ref)
            pax = pax_by_ref.get(ref, [])
            lead = pax[0] if pax else None
            phone = None
            if lead and (lead.phone or lead.phone_code):
                phone = f"{lead.phone_code or ''}{lead.phone or ''}".strip() or None
            hotel_code = str(booking.hotel_code or "").strip() or None
            hotel_name = str(booking.hotel_name or "").strip()
            items.append(
                HotelBookingListItemSerializer(
                    app_reference=ref,
                    status=booking.status,
                    payment_status=_payment_status_for(pay_by_ref.get(ref, [])),
                    booking_source=booking.booking_source,
                    booking_reference=booking.booking_reference,
                    confirmation_reference=booking.confirmation_reference,
                    hotel_name=hotel_name,
                    hotel_code=hotel_code,
                    hotel_location=booking.hotel_location,
                    check_in=str(booking.hotel_check_in) if booking.hotel_check_in else None,
                    check_out=str(booking.hotel_check_out) if booking.hotel_check_out else None,
                    rooms=int(booking.rooms or 1),
                    total_adults=int(booking.total_adults or 0),
                    total_children=int(booking.total_children or 0),
                    email=lead.email if lead else None,
                    phone=phone,
                    lead_guest_name=_guest_name(lead) if lead else None,
                    guest_count=len(pax),
                    room_summary=_room_summary(itin_by_ref.get(ref, [])),
                    total_fare=_money(txn.total) if txn else None,
                    currency=txn.currency if txn else None,
                    payment_mode=txn.payment_mode if txn else None,
                    created_at=booking.created_at,
                )
            )
        return items

    async def _lookup_crs_hotel(
        self, booking: HotelBookingDetailsRow
    ) -> HotelCrsHotelRow | None:
        if self._crs_session is None:
            return None

        crs_code = str(booking.hotel_crs_hotel_code or "").strip()
        if crs_code:
            by_code = (
                await self._crs_session.execute(
                    select(HotelCrsHotelRow).where(HotelCrsHotelRow.code == crs_code)
                )
            ).scalar_one_or_none()
            if by_code is not None:
                return by_code
            # Older rows may store CRS UUID in hotel_crs_hotel_code
            by_id = await self._crs_session.get(HotelCrsHotelRow, crs_code)
            if by_id is not None:
                return by_id

        supplier_code = str(booking.hotel_code or "").strip()
        if not supplier_code:
            return None
        row = (
            await self._crs_session.execute(
                select(HotelCrsHotelRow)
                .join(
                    HotelCrsSupplierHotelMapRow,
                    HotelCrsSupplierHotelMapRow.hotel_id == HotelCrsHotelRow.id,
                )
                .where(HotelCrsSupplierHotelMapRow.supplier_hotel_code == supplier_code)
                .where(HotelCrsHotelRow.status.is_(True))
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _primary_crs_image(self, hotel_id: str) -> str | None:
        if self._crs_session is None:
            return None
        url = (
            await self._crs_session.execute(
                select(HotelCrsHotelImageRow.url)
                .where(HotelCrsHotelImageRow.hotel_id == hotel_id)
                .order_by(
                    HotelCrsHotelImageRow.sort_order.asc(),
                    HotelCrsHotelImageRow.id.asc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return str(url).strip() if url else None

    async def get_details(self, app_reference: str) -> HotelBookingDetailSerializer | None:
        ref = app_reference.strip()
        booking = (
            await self._session.execute(
                select(HotelBookingDetailsRow).where(
                    HotelBookingDetailsRow.app_reference == ref,
                    HotelBookingDetailsRow.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if booking is None:
            return None

        txn = (
            await self._session.execute(
                select(HotelBookingTransactionDetailsRow).where(
                    HotelBookingTransactionDetailsRow.app_reference == ref
                )
            )
        ).scalar_one_or_none()

        guests = list(
            (
                await self._session.execute(
                    select(HotelBookingPaxDetailsRow)
                    .where(HotelBookingPaxDetailsRow.app_reference == ref)
                    .order_by(HotelBookingPaxDetailsRow.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        rooms = list(
            (
                await self._session.execute(
                    select(HotelBookingItineraryDetailsRow)
                    .where(HotelBookingItineraryDetailsRow.app_reference == ref)
                    .order_by(HotelBookingItineraryDetailsRow.created_at.asc())
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

        admin_currency = (txn.currency if txn else None) or "USD"
        rate = float(txn.conversion_rate) if txn and txn.conversion_rate else None
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
                line("Room rate", _money(txn.base_fare)),
                line("Taxes", _money(txn.taxes)),
                line("Admin markup", _money(txn.admin_markup)),
                line("Admin discount", _money(txn.admin_discount)),
                line("Supplier discount", _money(txn.discount)),
                line("Convenience fee", _money(txn.convenience_amount)),
            ]
            total_admin = _money(txn.total)
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
            )

        lead = guests[0] if guests else None
        phone = None
        if lead and (lead.phone or lead.phone_code):
            phone = f"{lead.phone_code or ''}{lead.phone or ''}".strip() or None

        hotel_name = str(booking.hotel_name or "").strip()
        hotel_address = booking.hotel_address
        hotel_location = booking.hotel_location
        hotel_image = booking.hotel_image
        star_rating = booking.star_rating
        hotel_code = str(booking.hotel_code or "").strip() or None
        hotel_crs_hotel_code = str(booking.hotel_crs_hotel_code or "").strip() or None

        crs_hotel = await self._lookup_crs_hotel(booking)
        if crs_hotel is not None:
            if not hotel_name:
                hotel_name = str(crs_hotel.name or "").strip()
            crs_address = _crs_address(crs_hotel)
            if not hotel_address and crs_address:
                hotel_address = crs_address
            if not hotel_location and crs_hotel.location:
                hotel_location = str(crs_hotel.location)
            if star_rating is None or int(star_rating or 0) <= 0:
                star_rating = int(crs_hotel.star_rating or 0) or None
            if not hotel_crs_hotel_code:
                hotel_crs_hotel_code = str(crs_hotel.code or "").strip() or None
            primary = str(crs_hotel.image or "").strip() or None
            if not primary:
                primary = await self._primary_crs_image(crs_hotel.id)
            if primary:
                hotel_image = primary

        return HotelBookingDetailSerializer(
            app_reference=booking.app_reference,
            status=booking.status,
            payment_status=_payment_status_for(payments),
            booking_source=booking.booking_source,
            booking_reference=booking.booking_reference,
            confirmation_reference=booking.confirmation_reference,
            hotel_name=hotel_name,
            hotel_address=hotel_address,
            hotel_location=hotel_location,
            hotel_image=hotel_image,
            star_rating=star_rating,
            hotel_code=hotel_code,
            hotel_crs_hotel_code=hotel_crs_hotel_code,
            check_in=str(booking.hotel_check_in) if booking.hotel_check_in else None,
            check_out=str(booking.hotel_check_out) if booking.hotel_check_out else None,
            check_in_time=booking.check_in_time or (crs_hotel.check_in_time if crs_hotel else None),
            check_out_time=booking.check_out_time
            or (crs_hotel.check_out_time if crs_hotel else None),
            rooms=int(booking.rooms or 1),
            total_adults=int(booking.total_adults or 0),
            total_children=int(booking.total_children or 0),
            email=lead.email if lead else None,
            phone=phone,
            lead_guest_name=_guest_name(lead) if lead else None,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            guests=[
                GuestDetailSerializer(
                    title=p.title,
                    first_name=p.first_name,
                    last_name=p.last_name,
                    pax_type=p.pax_type or "Adult",
                    email=p.email,
                    phone=p.phone,
                    phone_code=p.phone_code,
                )
                for p in guests
            ],
            room_lines=[
                RoomDetailSerializer(
                    room_type_name=r.room_type_name,
                    status=r.status,
                    adults=int(r.adults or 0),
                    children=int(r.children or 0),
                    base_fare=_money(r.base_fare),
                    taxes=_money(r.taxes),
                    hotel_crs_room_code=r.hotel_crs_room_code,
                )
                for r in rooms
            ],
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
        )

    async def export_csv(self, filters: HotelBookingListFilters) -> str:
        export_filters = filters.model_copy(update={"page": 1, "page_size": 100})
        all_items: list[HotelBookingListItemSerializer] = []
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
                "hotel_name",
                "hotel_code",
                "check_in",
                "check_out",
                "rooms",
                "lead_guest",
                "email",
                "total_fare",
                "currency",
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
                    item.hotel_name,
                    item.hotel_code or "",
                    item.check_in or "",
                    item.check_out or "",
                    item.rooms,
                    item.lead_guest_name or "",
                    item.email or "",
                    item.total_fare if item.total_fare is not None else "",
                    item.currency or "",
                    item.created_at.isoformat() if item.created_at else "",
                ]
            )
        return buf.getvalue()
