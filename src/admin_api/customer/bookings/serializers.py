from pydantic import AwareDatetime

from admin_api.customer.bookings.domainmodel import (
    BookingBizKpiSummaryDomainModel,
    CustomerBookingDomainModel,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel
from luxtj.domain.enums import (
    BookingSourceEnum,
    BookingStatusEnum,
    BookingTypeEnum,
    CustomerTierEnum,
    PaymentStatusEnum,
    RefundStatusEnum,
)


class BookingBizKpiSummary(ApiSerializerBaseModel):
    total_bookings: int
    total_booking_value: AmountSerializer
    net_revenue: AmountSerializer
    payment_success_rate: float
    cancellation_rate: float
    refund_rate: float

    @classmethod
    def from_domain_model(
        cls, biz_summary_model: BookingBizKpiSummaryDomainModel
    ) -> BookingBizKpiSummary:
        return cls(
            total_bookings=biz_summary_model.total_bookings,
            total_booking_value=AmountSerializer(
                amount=biz_summary_model.total_booking_value,
                currency=biz_summary_model.amount_currency,
            ),
            net_revenue=AmountSerializer(
                amount=biz_summary_model.net_revenue, currency=biz_summary_model.amount_currency
            ),
            payment_success_rate=biz_summary_model.payment_success_rate,
            cancellation_rate=biz_summary_model.cancellation_rate,
            refund_rate=biz_summary_model.refund_rate,
        )


class BookingCustomer(ApiSerializerBaseModel):
    user_id: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_tier: CustomerTierEnum
    user_phone_number: str

    @classmethod
    def from_domain_model(cls, domain_model: CustomerBookingDomainModel) -> BookingCustomer:
        return cls(
            user_id=domain_model.customer.user_id,
            user_first_name=domain_model.customer.user_first_name,
            user_last_name=domain_model.customer.user_last_name,
            user_email=domain_model.customer.user_email,
            user_tier=domain_model.customer.user_tier,
            user_phone_number=domain_model.customer.user_phone_number,
        )


class CustomerBookingLineItem(ApiSerializerBaseModel):
    booking_id: str
    customer: BookingCustomer
    booking_type: BookingTypeEnum
    booking_created_date: AwareDatetime
    travel_start_date: AwareDatetime
    booking_status: BookingStatusEnum
    booking_total_value: AmountSerializer
    booking_paid_value: AmountSerializer
    payment_status: PaymentStatusEnum
    cancellation_status: str  # Yes / No
    refund_status: RefundStatusEnum
    origin: str
    destination: str
    booking_source: BookingSourceEnum

    @classmethod
    def from_domain_model(
        cls, booking_domain_model: CustomerBookingDomainModel
    ) -> CustomerBookingLineItem:
        _cancellation_status = (
            "Yes" if booking_domain_model.booking_status == BookingStatusEnum.CANCELLED else "No"
        )
        return cls(
            booking_id=booking_domain_model.booking_id,
            customer=BookingCustomer.from_domain_model(booking_domain_model),
            booking_type=BookingTypeEnum(booking_domain_model.booking_type),
            booking_created_date=booking_domain_model.booking_created_at,
            travel_start_date=booking_domain_model.travel_start_at,
            booking_status=BookingStatusEnum(booking_domain_model.booking_status),
            booking_total_value=AmountSerializer(
                amount=booking_domain_model.booking_total_amount,
                currency=booking_domain_model.amount_currency,
            ),
            booking_paid_value=AmountSerializer(
                amount=booking_domain_model.booking_paid_amount,
                currency=booking_domain_model.amount_currency,
            ),
            payment_status=PaymentStatusEnum(booking_domain_model.payment_status),
            cancellation_status=_cancellation_status,
            refund_status=RefundStatusEnum(booking_domain_model.refund_status),
            origin=booking_domain_model.origin_location,
            destination=booking_domain_model.destination_location,
            booking_source=BookingSourceEnum(booking_domain_model.booking_source),
        )
