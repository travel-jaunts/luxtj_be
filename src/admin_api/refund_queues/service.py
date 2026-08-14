"""Admin flight + hotel refund queue queries."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_api.refund_queues.serializers import (
    FlightRefundIssueResultSerializer,
    FlightRefundQueueItemSerializer,
    FlightRefundQueueListBody,
    FlightRefundQueueListResultSerializer,
    HotelRefundIssueResultSerializer,
    HotelRefundQueueItemSerializer,
    HotelRefundQueueListBody,
    HotelRefundQueueListResultSerializer,
)
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import (
    FlightBookingDetailsRow,
    FlightBookingPassengerDetailsRow,
)
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
    HotelBookingDetailsRow,
    HotelBookingPaxDetailsRow,
)
from luxtj.contexts.integration.domain.catalog import (
    PAYMENT_GATEWAYS,
    gateway_supports_refund_api,
)
from luxtj.contexts.payment.application.service import PaymentGatewayService
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_models import (
    PaymentGatewayTransactionRow,
)
from luxtj.contexts.payment.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyPaymentGatewayTransactionRepository,
)

_FLIGHT_QUEUE_BOOKING_STATUSES = ("BOOKING_FAILED", "BOOKING_CANCELLED")
_HOTEL_QUEUE_BOOKING_STATUSES = ("BOOKING_FAILED", "CANCELLED", "BOOKING_CANCELLED")
_QUEUE_PAYMENT_STATUSES = ("accepted", "partially_refunded")


def _pax_name(
    p: FlightBookingPassengerDetailsRow | HotelBookingPaxDetailsRow | None,
) -> str | None:
    if p is None:
        return None
    parts = [p.title or "", p.first_name or "", p.last_name or ""]
    name = " ".join(x for x in parts if x).strip()
    return name or None


def _phone_from_hotel_pax(p: HotelBookingPaxDetailsRow | None) -> str | None:
    if p is None:
        return None
    code = str(p.phone_code or "").strip()
    phone = str(p.phone or "").strip()
    if code and phone:
        return f"{code}{phone}" if code.startswith("+") else f"+{code}{phone}"
    return phone or None


async def _issue_payment_refund(
    session: AsyncSession,
    http_client: Any,
    *,
    transaction_id: str,
    refund_amount: float,
    remark: str | None,
    manual_details: str | None,
    admin_user_id: str | None,
) -> dict[str, Any]:
    pay_svc = PaymentGatewayService(
        repository=SqlAlchemyPaymentGatewayTransactionRepository(session),
        http_client=http_client,
    )
    result = await pay_svc.issue_refund(
        transaction_id=transaction_id,
        refund_amount=Decimal(str(refund_amount)),
        remark=remark,
        manual_details=manual_details,
        admin_user_id=admin_user_id,
    )
    if not result.get("status"):
        raise ValueError(str(result.get("message") or "Refund failed"))
    return result


class FlightRefundQueueService:
    def __init__(self, session: AsyncSession, *, http_client: Any) -> None:
        self._session = session
        self._http = http_client

    async def list_queue(
        self, body: FlightRefundQueueListBody
    ) -> FlightRefundQueueListResultSerializer:
        booking_status = (body.booking_status or "").strip()
        statuses = (
            (booking_status,)
            if booking_status and booking_status in _FLIGHT_QUEUE_BOOKING_STATUSES
            else _FLIGHT_QUEUE_BOOKING_STATUSES
        )

        stmt = (
            select(FlightBookingDetailsRow, PaymentGatewayTransactionRow)
            .join(
                PaymentGatewayTransactionRow,
                PaymentGatewayTransactionRow.app_reference == FlightBookingDetailsRow.app_reference,
            )
            .where(
                FlightBookingDetailsRow.status.in_(statuses),
                PaymentGatewayTransactionRow.status.in_(_QUEUE_PAYMENT_STATUSES),
            )
        )

        search = (body.search or "").strip()
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    FlightBookingDetailsRow.app_reference.ilike(like),
                    FlightBookingDetailsRow.email.ilike(like),
                    FlightBookingDetailsRow.gdspnr.ilike(like),
                    PaymentGatewayTransactionRow.transaction_id.ilike(like),
                )
            )

        stmt = stmt.where(
            PaymentGatewayTransactionRow.amount
            > func.coalesce(PaymentGatewayTransactionRow.refunded_amount, 0)
        )

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        page = body.page
        page_size = body.page_size
        rows = list(
            (
                await self._session.execute(
                    stmt.order_by(PaymentGatewayTransactionRow.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )

        refs = [booking.app_reference for booking, _pay in rows]
        lead_by_ref: dict[str, FlightBookingPassengerDetailsRow] = {}
        if refs:
            pax_rows = list(
                (
                    await self._session.execute(
                        select(FlightBookingPassengerDetailsRow)
                        .where(FlightBookingPassengerDetailsRow.app_reference.in_(refs))
                        .order_by(FlightBookingPassengerDetailsRow.created_at.asc())
                    )
                )
                .scalars()
                .all()
            )
            for pax in pax_rows:
                lead_by_ref.setdefault(pax.app_reference, pax)

        items: list[FlightRefundQueueItemSerializer] = []
        for booking, pay in rows:
            paid = float(pay.amount or 0)
            refunded = float(pay.refunded_amount or 0)
            refundable = max(0.0, paid - refunded)
            supports = gateway_supports_refund_api(pay.pg_code)
            catalog = PAYMENT_GATEWAYS.get(str(pay.pg_code or "").lower())
            items.append(
                FlightRefundQueueItemSerializer(
                    app_reference=booking.app_reference,
                    booking_status=booking.status,
                    booking_source=booking.booking_source,
                    email=booking.email,
                    phone=booking.phone,
                    lead_passenger_name=_pax_name(lead_by_ref.get(booking.app_reference)),
                    origin=booking.origin,
                    destination=booking.destination,
                    trip_type=booking.trip_type,
                    booking_created_at=booking.created_at,
                    transaction_id=pay.transaction_id,
                    pg_code=pay.pg_code,
                    payment_status=pay.status,
                    paid_amount=paid,
                    refunded_amount=refunded,
                    refundable_amount=refundable,
                    currency=pay.currency,
                    supports_refund_api=supports,
                    refund_api=catalog.refund_api if catalog else "no",
                    payment_created_at=pay.created_at,
                )
            )

        return FlightRefundQueueListResultSerializer(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def issue_refund(
        self,
        *,
        transaction_id: str,
        refund_amount: float,
        remark: str | None,
        manual_details: str | None,
        admin_user_id: str | None,
    ) -> FlightRefundIssueResultSerializer:
        result = await _issue_payment_refund(
            self._session,
            self._http,
            transaction_id=transaction_id,
            refund_amount=refund_amount,
            remark=remark,
            manual_details=manual_details,
            admin_user_id=admin_user_id,
        )
        return FlightRefundIssueResultSerializer(
            transaction_id=str(result.get("transaction_id") or transaction_id),
            app_reference=str(result.get("app_reference") or ""),
            payment_status=str(result.get("payment_status") or ""),
            refund_mode=str(result.get("refund_mode") or ""),
            refunded_amount=float(result.get("refunded_amount") or 0),
            refund_amount_this_request=float(result.get("refund_amount_this_request") or 0),
            currency=str(result.get("currency") or ""),
            supports_refund_api=bool(result.get("supports_refund_api")),
            message=str(result.get("message") or "Refund processed"),
        )


class HotelRefundQueueService:
    def __init__(self, session: AsyncSession, *, http_client: Any) -> None:
        self._session = session
        self._http = http_client

    async def list_queue(
        self, body: HotelRefundQueueListBody
    ) -> HotelRefundQueueListResultSerializer:
        booking_status = (body.booking_status or "").strip()
        statuses = (
            (booking_status,)
            if booking_status and booking_status in _HOTEL_QUEUE_BOOKING_STATUSES
            else _HOTEL_QUEUE_BOOKING_STATUSES
        )

        stmt = (
            select(HotelBookingDetailsRow, PaymentGatewayTransactionRow)
            .join(
                PaymentGatewayTransactionRow,
                PaymentGatewayTransactionRow.app_reference == HotelBookingDetailsRow.app_reference,
            )
            .where(
                HotelBookingDetailsRow.status.in_(statuses),
                HotelBookingDetailsRow.deleted_at.is_(None),
                PaymentGatewayTransactionRow.status.in_(_QUEUE_PAYMENT_STATUSES),
            )
        )

        search = (body.search or "").strip()
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    HotelBookingDetailsRow.app_reference.ilike(like),
                    HotelBookingDetailsRow.hotel_name.ilike(like),
                    HotelBookingDetailsRow.booking_reference.ilike(like),
                    HotelBookingDetailsRow.confirmation_reference.ilike(like),
                    PaymentGatewayTransactionRow.transaction_id.ilike(like),
                )
            )

        stmt = stmt.where(
            PaymentGatewayTransactionRow.amount
            > func.coalesce(PaymentGatewayTransactionRow.refunded_amount, 0)
        )

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        page = body.page
        page_size = body.page_size
        rows = list(
            (
                await self._session.execute(
                    stmt.order_by(PaymentGatewayTransactionRow.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )

        refs = [booking.app_reference for booking, _pay in rows]
        lead_by_ref: dict[str, HotelBookingPaxDetailsRow] = {}
        if refs:
            pax_rows = list(
                (
                    await self._session.execute(
                        select(HotelBookingPaxDetailsRow)
                        .where(HotelBookingPaxDetailsRow.app_reference.in_(refs))
                        .order_by(HotelBookingPaxDetailsRow.created_at.asc())
                    )
                )
                .scalars()
                .all()
            )
            for pax in pax_rows:
                lead_by_ref.setdefault(pax.app_reference, pax)

        items: list[HotelRefundQueueItemSerializer] = []
        for booking, pay in rows:
            lead = lead_by_ref.get(booking.app_reference)
            paid = float(pay.amount or 0)
            refunded = float(pay.refunded_amount or 0)
            refundable = max(0.0, paid - refunded)
            supports = gateway_supports_refund_api(pay.pg_code)
            catalog = PAYMENT_GATEWAYS.get(str(pay.pg_code or "").lower())
            items.append(
                HotelRefundQueueItemSerializer(
                    app_reference=booking.app_reference,
                    booking_status=booking.status,
                    booking_source=booking.booking_source,
                    email=(lead.email if lead else None),
                    phone=_phone_from_hotel_pax(lead),
                    lead_guest_name=_pax_name(lead),
                    hotel_name=booking.hotel_name,
                    hotel_location=booking.hotel_location,
                    check_in=booking.hotel_check_in.isoformat() if booking.hotel_check_in else None,
                    check_out=booking.hotel_check_out.isoformat()
                    if booking.hotel_check_out
                    else None,
                    booking_created_at=booking.created_at,
                    transaction_id=pay.transaction_id,
                    pg_code=pay.pg_code,
                    payment_status=pay.status,
                    paid_amount=paid,
                    refunded_amount=refunded,
                    refundable_amount=refundable,
                    currency=pay.currency,
                    supports_refund_api=supports,
                    refund_api=catalog.refund_api if catalog else "no",
                    payment_created_at=pay.created_at,
                )
            )

        return HotelRefundQueueListResultSerializer(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def issue_refund(
        self,
        *,
        transaction_id: str,
        refund_amount: float,
        remark: str | None,
        manual_details: str | None,
        admin_user_id: str | None,
    ) -> HotelRefundIssueResultSerializer:
        result = await _issue_payment_refund(
            self._session,
            self._http,
            transaction_id=transaction_id,
            refund_amount=refund_amount,
            remark=remark,
            manual_details=manual_details,
            admin_user_id=admin_user_id,
        )
        return HotelRefundIssueResultSerializer(
            transaction_id=str(result.get("transaction_id") or transaction_id),
            app_reference=str(result.get("app_reference") or ""),
            payment_status=str(result.get("payment_status") or ""),
            refund_mode=str(result.get("refund_mode") or ""),
            refunded_amount=float(result.get("refunded_amount") or 0),
            refund_amount_this_request=float(result.get("refund_amount_this_request") or 0),
            currency=str(result.get("currency") or ""),
            supports_refund_api=bool(result.get("supports_refund_api")),
            message=str(result.get("message") or "Refund processed"),
        )
