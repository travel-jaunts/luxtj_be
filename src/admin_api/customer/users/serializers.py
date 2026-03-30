from pydantic import Field, AwareDatetime

from common.serializerlib import ApiSerializerBaseModel, AmountSerializer
from admin_api.customer.users.domainmodel import (
    CustomerDomainModel,
    CustomerTierEnum,
    CustomerBizKpiSummaryDomainModel,
)


class CustomerBizKpiSummary(ApiSerializerBaseModel):
    total_revenue: AmountSerializer
    average_order_value: AmountSerializer
    total_customers: int
    active_customers: int
    repeat_rate: float = Field(
        ..., description="Percentage of customers who made more than one purchase"
    )
    cancellation_rate: float = Field(..., description="Percentage of orders that were cancelled")
    customers_by_tier: dict[CustomerTierEnum, int]

    @classmethod
    def from_domain_model(
        cls, biz_summary_model: CustomerBizKpiSummaryDomainModel
    ) -> "CustomerBizKpiSummary":
        return cls(
            total_revenue=AmountSerializer(
                amount=biz_summary_model.total_revenue, currency=biz_summary_model.amount_currency
            ),
            average_order_value=AmountSerializer(
                amount=biz_summary_model.average_order_value,
                currency=biz_summary_model.amount_currency,
            ),
            total_customers=biz_summary_model.total_customers,
            active_customers=biz_summary_model.active_customers,
            repeat_rate=biz_summary_model.repeat_rate,
            cancellation_rate=biz_summary_model.cancellation_rate,
            customers_by_tier=biz_summary_model.customers_by_tier,
        )


class CustomerListItem(ApiSerializerBaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    base_location: str
    registration_date: AwareDatetime
    last_booking_date: AwareDatetime | None = Field(
        None, description="The date of the user's last booking, if available"
    )
    total_spend: AmountSerializer = Field(
        ..., description="Total amount spent by the user across all bookings"
    )
    booking_count: int = Field(..., description="Total number of bookings made by the user")
    average_order_value: AmountSerializer = Field(
        ..., description="Average order value of the user across all bookings"
    )
    cancellation_count: int = Field(
        ..., description="Total number of bookings cancelled by the user"
    )
    cancellation_rate: float = Field(
        ..., description="Percentage of the user's bookings that were cancelled"
    )
    is_active: bool = Field(True, description="Indicates if the user account is active or not")
    tier: CustomerTierEnum = Field(
        CustomerTierEnum.NOVUS,
        description="The tier of the user (Novus, Aurea, Privé, Elite, Échelon)",
    )
    status: str = Field(..., description="Current status of the user (e.g., Active, Inactive)")

    @classmethod
    def from_domain_model(cls, customer_model: CustomerDomainModel) -> "CustomerListItem":
        return cls(
            customer_id=customer_model.user_id,
            first_name=customer_model.user_first_name,
            last_name=customer_model.user_last_name,
            email=customer_model.user_email,
            phone_number=customer_model.user_phone_number,
            base_location=customer_model.user_base_location,
            registration_date=customer_model.user_registration_date,
            last_booking_date=customer_model.user_last_booking_date,  # This would need to be calculated based on booking data
            total_spend=AmountSerializer(
                amount=customer_model.user_total_spend, currency=customer_model.user_amount_currency
            ),  # Placeholder
            booking_count=customer_model.user_booking_count,  # This would need to be calculated based on
            average_order_value=AmountSerializer(
                amount=customer_model.user_average_order_value,
                currency=customer_model.user_amount_currency,
            ),  # Placeholder
            cancellation_count=customer_model.user_cancellation_count,  # This would need to be calculated based
            cancellation_rate=customer_model.user_cancellation_rate,  # This would need to be calculated based on booking data
            is_active=customer_model.user_is_active,
            tier=CustomerTierEnum(customer_model.user_tier),
            status=customer_model.user_status,
        )
