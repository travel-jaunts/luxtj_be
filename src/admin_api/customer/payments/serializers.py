from pydantic import AwareDatetime

from admin_api.customer.payments.domainmodel import (
    PaymentRefundKpiSummaryDomainModel,
    CustomerPaymentDomainModel,
)
from admin_api.customer.users.domainmodel import CustomerDomainModel
from common.serializerlib import ApiSerializerBaseModel, AmountSerializer
from luxtj.domain.enums import (
    CustomerTierEnum,
    TransactionTypeEnum,
    PaymentStatusEnum,
    PaymentMethodEnum,
    PaymentSourceEnum,
)


class TransactionCustomer(ApiSerializerBaseModel):
    user_id: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_tier: CustomerTierEnum
    user_phone_number: str

    @classmethod
    def from_domain_model(cls, customer_model: CustomerDomainModel) -> "TransactionCustomer":
        return cls(
            user_id=customer_model.user_id,
            user_first_name=customer_model.user_first_name,
            user_last_name=customer_model.user_last_name,
            user_email=customer_model.user_email,
            user_tier=customer_model.user_tier,
            user_phone_number=customer_model.user_phone_number,
        )


class PaymentRefundKpiSummarySerializer(ApiSerializerBaseModel):
    gross_booking_value: AmountSerializer
    total_payments_received: int
    total_refunds_issued: int
    net_revenue: AmountSerializer
    outstanding_receivables: AmountSerializer
    reconciliation_accuracy_rate: float
    unsuccessfull_payments_count: int

    @classmethod
    def from_domain_model(
        cls, payment_summary_domain_model: PaymentRefundKpiSummaryDomainModel
    ) -> "PaymentRefundKpiSummarySerializer":
        return cls(
            gross_booking_value=AmountSerializer(
                amount=payment_summary_domain_model.gross_booking_value,
                currency=payment_summary_domain_model.amount_currency,
            ),
            total_payments_received=payment_summary_domain_model.total_payments_received,
            total_refunds_issued=payment_summary_domain_model.total_refunds_issued,
            net_revenue=AmountSerializer(
                amount=payment_summary_domain_model.net_revenue,
                currency=payment_summary_domain_model.amount_currency,
            ),
            outstanding_receivables=AmountSerializer(
                amount=payment_summary_domain_model.outstanding_receivables,
                currency=payment_summary_domain_model.amount_currency,
            ),
            reconciliation_accuracy_rate=payment_summary_domain_model.reconciliation_accuracy_rate,
            unsuccessfull_payments_count=payment_summary_domain_model.unsuccessfull_payments_count,
        )


class PaymentsLineItem(ApiSerializerBaseModel):
    transaction_id: str
    customer: TransactionCustomer
    transaction_type: TransactionTypeEnum
    order_id: str | None
    order_value: AmountSerializer
    transaction_method: PaymentMethodEnum
    transaction_status: PaymentStatusEnum
    transaction_timestamp: AwareDatetime
    transaction_source: PaymentSourceEnum
    transaction_source_reference: str

    @classmethod
    def from_domain_model(
        cls, payment_domain_model: CustomerPaymentDomainModel
    ) -> "PaymentsLineItem":
        return cls(
            transaction_id=payment_domain_model.transaction_id,
            customer=TransactionCustomer.from_domain_model(payment_domain_model.customer),
            transaction_type=payment_domain_model.transaction_type,
            order_id=payment_domain_model.booking_id,
            order_value=AmountSerializer(
                amount=payment_domain_model.transaction_amount,
                currency=payment_domain_model.transaction_currency,
            ),
            transaction_method=payment_domain_model.transaction_method,
            transaction_status=payment_domain_model.transaction_status,
            transaction_timestamp=payment_domain_model.transaction_timestamp,
            transaction_source=payment_domain_model.transaction_source,
            transaction_source_reference=payment_domain_model.transaction_source_reference,
        )
