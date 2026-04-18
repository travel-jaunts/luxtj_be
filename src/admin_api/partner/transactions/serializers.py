from pydantic import AwareDatetime

from admin_api.partner.transactions.domainmodel import (
    PartnerPaymentLineItemDomainModel,
    PartnerPaymentStatusEnum,
    PartnerPaymentTypeEnum,
    PartnerRefundLineItemDomainModel,
    PartnerRefundStatusEnum,
    PartnerTransactionsSummaryDomainModel,
)

from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class PartnerTransactionsSummary(ApiSerializerBaseModel):
    total_partner_payments: AmountSerializer
    pending_payments: AmountSerializer
    refunds_pending: AmountSerializer
    completed_payments: AmountSerializer

    @classmethod
    def from_domain_model(
        cls, domain_model: PartnerTransactionsSummaryDomainModel
    ) -> "PartnerTransactionsSummary":
        return cls(
            total_partner_payments=AmountSerializer(
                amount=domain_model.total_partner_payments_amount,
                currency=domain_model.amount_currency,
            ),
            pending_payments=AmountSerializer(
                amount=domain_model.pending_payments_amount,
                currency=domain_model.amount_currency,
            ),
            refunds_pending=AmountSerializer(
                amount=domain_model.refunds_pending_amount,
                currency=domain_model.amount_currency,
            ),
            completed_payments=AmountSerializer(
                amount=domain_model.completed_payments_amount,
                currency=domain_model.amount_currency,
            ),
        )


class PartnerPaymentsLineItem(ApiSerializerBaseModel):
    payment_id: str
    partner: str
    payment_type: PartnerPaymentTypeEnum
    amount: AmountSerializer
    booking_id: str
    status: PartnerPaymentStatusEnum
    date: AwareDatetime

    @classmethod
    def from_domain_model(
        cls, domain_model: PartnerPaymentLineItemDomainModel
    ) -> "PartnerPaymentsLineItem":
        return cls(
            payment_id=domain_model.payment_id,
            partner=domain_model.partner,
            payment_type=domain_model.payment_type,
            amount=AmountSerializer(amount=domain_model.amount, currency=domain_model.currency),
            booking_id=domain_model.booking_id,
            status=domain_model.status,
            date=domain_model.date,
        )


class PartnerRefundsLineItem(ApiSerializerBaseModel):
    refund_id: str
    booking: str
    customer: str
    amount: AmountSerializer
    reason: str
    status: PartnerRefundStatusEnum

    @classmethod
    def from_domain_model(
        cls, domain_model: PartnerRefundLineItemDomainModel
    ) -> "PartnerRefundsLineItem":
        return cls(
            refund_id=domain_model.refund_id,
            booking=domain_model.booking,
            customer=domain_model.customer,
            amount=AmountSerializer(amount=domain_model.amount, currency=domain_model.currency),
            reason=domain_model.reason,
            status=domain_model.status,
        )


