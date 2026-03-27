from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Query, Path
from pydantic import Field, AwareDatetime

from common.serializerlib import (
    ApiSerializerBaseModel,
    RequestProcessStatus,
    ApiSuccessResponse,
    PaginationParams,
    PaginatedResult,
)


class BookingStatusEnum(StrEnum):
    """Enum to represent different booking statuses (e.g., Confirmed, Cancelled, Pending)
    - more statuses to be added
    """

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class BookingSourceEnum(StrEnum):
    """Enum to represent different booking sources (e.g., Website, Mobile App, Third-Party)
    - more sources to be added
    """

    AFFILIATE = "affiliate"
    MOBILE_APP = "mobile_app"
    WEB_APP = "web_app"
    B2B_AGENT = "b2b_agent"


class PaymentStatusEnum(StrEnum):
    """Enum to represent different payment statuses (e.g., Completed, Failed, Refunded)
    - more statuses to be added
    """

    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethodEnum(StrEnum):
    """Enum to represent different payment methods (e.g., Credit Card, PayPal, Bank Transfer)
    - more methods to be added
    """

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"


class PaymentSourceEnum(StrEnum):
    """Enum to represent different payment sources (e.g., Website, Mobile App, Third-Party)
    - more sources to be added
    """

    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"


class UserTierEnum(StrEnum):
    """Enum to represent different user tiers (e.g., Standard, World Wise)
    - more tiers to be added
    """

    NOVUS = "Novus"
    AUREA = "Aurea"
    PRIVE = "Privé"
    ELITE = "Elite"
    ECHELON = "Échelon"


class SupportTicketPriorityEnum(StrEnum):
    """Enum to represent different support ticket priorities (e.g., Low, Medium, High)
    - more priorities to be added
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# line item models --------------------------------------------------------------------------------
class UserListItem(ApiSerializerBaseModel):
    user_id: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_registration_date: AwareDatetime
    user_is_active: bool = Field(True, description="Indicates if the user account is active or not")
    user_tier: UserTierEnum = Field(
        UserTierEnum.NOVUS, description="The tier of the user (Novus, Aurea, Privé, Elite, Échelon)"
    )
    user_phone_number: str
    user_base_location: str


class CustomerBookingLineItem(ApiSerializerBaseModel):
    booking_id: str
    customer: UserListItem
    booking_type: str
    booking_source: BookingSourceEnum
    booking_created_date: AwareDatetime
    booking_currency: str
    booking_amount: float
    travel_from_date: AwareDatetime
    travel_from_location: str
    travel_to_location: str
    travel_to_date: AwareDatetime
    booking_status: BookingStatusEnum
    booking_transaction_reference: str | None


class PaymentsLineItem(ApiSerializerBaseModel):
    payment_id: str
    payment_method: PaymentMethodEnum
    payment_source: PaymentSourceEnum
    customer: UserListItem
    booking_id: str
    payment_date: AwareDatetime
    payment_currency: str
    payment_amount: float = Field(..., description="Amount of the payment", ge=0)
    payment_status: PaymentStatusEnum
    payment_transaction_reference: str


class RefundsLineItem(ApiSerializerBaseModel):
    refund_id: str
    customer: UserListItem
    booking_id: str
    payment: PaymentsLineItem
    refund_date: AwareDatetime
    payment_currency: str
    payment_amount: float = Field(..., description="Amount of the payment", ge=0)
    payment_transaction_reference: str


class OfferLineItem(ApiSerializerBaseModel):
    offer_id: str
    offer_type: str
    offer_is_active: bool = Field(
        False, description="Indicates if the offer is currently active or not"
    )
    offer_title: str
    offer_description: str
    offer_valid_from: AwareDatetime
    offer_valid_to: AwareDatetime | None


class AgentDetailModel(ApiSerializerBaseModel):
    agent_id: str
    agent_first_name: str
    agent_last_name: str
    agent_email: str
    agent_phone_number: str


class SupportTicketLineItem(ApiSerializerBaseModel):
    ticket_id: str
    customer: UserListItem
    booking_id: str | None
    ticket_created_date: AwareDatetime
    ticket_status: str
    ticket_subject: str
    ticket_description: str
    ticket_resolution_date: AwareDatetime | None
    ticket_resolution_details: str | None  # a str generated from work log in the ticket
    ticket_priority: SupportTicketPriorityEnum
    assigned_agent: AgentDetailModel


# -------------------------------------------------------------------------------------------------
class RefundDetailSerializer(ApiSerializerBaseModel):
    refund_id: str
    customer: UserListItem
    booking: CustomerBookingLineItem
    payment: PaymentsLineItem
    refund_date: AwareDatetime
    payment_currency: str
    payment_amount: float
    payment_transaction_reference: str
    payment_status: PaymentStatusEnum


# =================================================================================================
customer_router = APIRouter(prefix="/customers")


@customer_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[UserListItem]],
    status_code=200,
    summary="List customers with pagination and filtering",
    name="List Customers",
)
async def list_customers(
    query: PaginationParams = Query(...),
) -> ApiSuccessResponse[PaginatedResult[UserListItem]]:
    """
    List customers with pagination
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=100,  # Replace with actual total count from database
            page=query.page,
            size=query.size,
            items=[
                UserListItem(
                    user_id="1",
                    user_first_name="John",
                    user_last_name="Doe",
                    user_email="john.doe@example.com",
                    user_registration_date=datetime.now(tz=timezone.utc),
                    user_is_active=True,
                    user_tier=UserTierEnum.NOVUS,
                    user_phone_number="+1234567890",
                    user_base_location="New York, USA",
                ),
                UserListItem(
                    user_id="2",
                    user_first_name="Jane",
                    user_last_name="Smith",
                    user_email="jane.smith@example.com",
                    user_registration_date=datetime.now(tz=timezone.utc),
                    user_is_active=False,
                    user_tier=UserTierEnum.AUREA,
                    user_phone_number="+0987654321",
                    user_base_location="London, UK",
                ),
            ],
        ),
    )


@customer_router.post(
    "/bookings/list",
    response_model=ApiSuccessResponse[PaginatedResult[CustomerBookingLineItem]],
    status_code=200,
    summary="List bookings for all customers with pagination and filtering",
    name="List Customer Bookings",
)
async def list_customer_bookings(
    query: PaginationParams = Query(...),
) -> ApiSuccessResponse[PaginatedResult[CustomerBookingLineItem]]:
    """
    List bookings for all customers with pagination
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=50,  # Replace with actual total count from database
            page=query.page,
            size=query.size,
            items=[
                CustomerBookingLineItem(
                    booking_id="b1",
                    customer=UserListItem(
                        user_id="1",
                        user_first_name="John",
                        user_last_name="Doe",
                        user_email="john.doe@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=True,
                        user_tier=UserTierEnum.NOVUS,
                        user_phone_number="+1234567890",
                        user_base_location="New York, USA",
                    ),
                    booking_type="flight",
                    booking_source=BookingSourceEnum.WEB_APP,
                    booking_created_date=datetime.now(tz=timezone.utc),
                    booking_currency="USD",
                    booking_amount=100.0,
                    travel_from_date=datetime(2024, 7, 1, tzinfo=timezone.utc),
                    travel_to_date=datetime(2024, 7, 10, tzinfo=timezone.utc),
                    travel_from_location="New York, USA",
                    travel_to_location="Los Angeles, USA",
                    booking_status=BookingStatusEnum.CONFIRMED,
                    booking_transaction_reference="txn_12345",
                ),
                CustomerBookingLineItem(
                    booking_id="b2",
                    customer=UserListItem(
                        user_id="2",
                        user_first_name="Jane",
                        user_last_name="Smith",
                        user_email="jane.smith@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=False,
                        user_tier=UserTierEnum.AUREA,
                        user_phone_number="+0987654321",
                        user_base_location="London, UK",
                    ),
                    booking_type="hotel",
                    booking_source=BookingSourceEnum.B2B_AGENT,
                    booking_created_date=datetime.now(tz=timezone.utc),
                    booking_currency="USD",
                    booking_amount=150.0,
                    travel_from_date=datetime(2024, 8, 1, tzinfo=timezone.utc),
                    travel_to_date=datetime(2024, 8, 10, tzinfo=timezone.utc),
                    travel_from_location="London, UK",
                    travel_to_location="Paris, France",
                    booking_status=BookingStatusEnum.CANCELLED,
                    booking_transaction_reference="txn_67890",
                ),
            ],
        ),
    )


@customer_router.post(
    "/payments/list",
    response_model=ApiSuccessResponse[PaginatedResult[PaymentsLineItem]],
    status_code=200,
    summary="List payments for all customers with pagination and filtering",
    name="List Customer Payments",
)
async def list_customer_payments(
    query: PaginationParams = Query(...),
) -> ApiSuccessResponse[PaginatedResult[PaymentsLineItem]]:
    """
    List payments and refunds for all customers with pagination
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=30,  # Replace with actual total count from database
            page=query.page,
            size=query.size,
            items=[
                PaymentsLineItem(
                    payment_id="p1",
                    payment_method=PaymentMethodEnum.CREDIT_CARD,
                    payment_source=PaymentSourceEnum.STRIPE,
                    customer=UserListItem(
                        user_id="1",
                        user_first_name="John",
                        user_last_name="Doe",
                        user_email="john.doe@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=True,
                        user_tier=UserTierEnum.NOVUS,
                        user_phone_number="+1234567890",
                        user_base_location="New York, USA",
                    ),
                    booking_id="b1",
                    payment_date=datetime.now(tz=timezone.utc),
                    payment_currency="USD",
                    payment_amount=100.0,
                    payment_transaction_reference="txn_12345",
                    payment_status=PaymentStatusEnum.COMPLETED,
                ),  # Replace with actual payment/refund models
                PaymentsLineItem(
                    payment_id="r1",
                    payment_method=PaymentMethodEnum.CREDIT_CARD,
                    payment_source=PaymentSourceEnum.STRIPE,
                    customer=UserListItem(
                        user_id="2",
                        user_first_name="Jane",
                        user_last_name="Smith",
                        user_email="jane.smith@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=False,
                        user_tier=UserTierEnum.AUREA,
                        user_phone_number="+0987654321",
                        user_base_location="London, UK",
                    ),
                    booking_id="b2",
                    payment_date=datetime.now(tz=timezone.utc),
                    payment_currency="USD",
                    payment_amount=50.0,
                    payment_transaction_reference="txn_67890",
                    payment_status=PaymentStatusEnum.REFUNDED,
                ),
            ],
        ),
    )


@customer_router.post(
    "/refunds/list",
    response_model=ApiSuccessResponse[PaginatedResult[RefundsLineItem]],
    status_code=200,
    summary="List refunds for all customers with pagination and filtering",
    name="List Customer Refunds",
)
async def list_customer_refunds(
    query: PaginationParams = Query(...),
) -> ApiSuccessResponse[PaginatedResult[RefundsLineItem]]:
    """
    List refunds for all customers with pagination
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=10,  # Replace with actual total count from database
            page=query.page,
            size=query.size,
            items=[
                RefundsLineItem(
                    refund_id="r1",
                    customer=UserListItem(
                        user_id="2",
                        user_first_name="Jane",
                        user_last_name="Smith",
                        user_email="jane.smith@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=False,
                        user_tier=UserTierEnum.AUREA,
                        user_phone_number="+0987654321",
                        user_base_location="London, UK",
                    ),
                    booking_id="b2",
                    payment=PaymentsLineItem(
                        payment_id="r1",
                        payment_method=PaymentMethodEnum.CREDIT_CARD,
                        payment_source=PaymentSourceEnum.STRIPE,
                        customer=UserListItem(
                            user_id="2",
                            user_first_name="Jane",
                            user_last_name="Smith",
                            user_email="jane.smith@example.com",
                            user_registration_date=datetime.now(tz=timezone.utc),
                            user_is_active=False,
                            user_tier=UserTierEnum.AUREA,
                            user_phone_number="+0987654321",
                            user_base_location="London, UK",
                        ),
                        booking_id="b2",
                        payment_date=datetime.now(tz=timezone.utc),
                        payment_currency="USD",
                        payment_amount=150.0,
                        payment_transaction_reference="txn_67890",
                        payment_status=PaymentStatusEnum.REFUNDED,
                    ),
                    refund_date=datetime.now(tz=timezone.utc),
                    payment_currency="USD",
                    payment_amount=50.0,
                    payment_transaction_reference="txn_67890",
                ),
            ],
        ),
    )


@customer_router.post(
    "/refunds/{refund_id}/details",
    response_model=ApiSuccessResponse[RefundDetailSerializer],
    status_code=200,
    summary="Get refund details for a specific refund",
    name="Get Refund Details",
)
async def get_refund_details(
    refund_id: Annotated[str, Path(..., description="The ID of the refund")],
) -> ApiSuccessResponse[RefundDetailSerializer]:
    """
    Get refund details for a specific refund
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=RefundDetailSerializer(
            refund_id=refund_id,
            customer=UserListItem(
                user_id="2",
                user_first_name="Jane",
                user_last_name="Smith",
                user_email="jane.smith@example.com",
                user_registration_date=datetime.now(tz=timezone.utc),
                user_is_active=False,
                user_tier=UserTierEnum.ECHELON,
                user_phone_number="+0987654321",
                user_base_location="London, UK",
            ),
            booking=CustomerBookingLineItem(
                booking_id="b2",
                customer=UserListItem(
                    user_id="2",
                    user_first_name="Jane",
                    user_last_name="Smith",
                    user_email="jane.smith@example.com",
                    user_registration_date=datetime.now(tz=timezone.utc),
                    user_is_active=False,
                    user_tier=UserTierEnum.ECHELON,
                    user_phone_number="+0987654321",
                    user_base_location="London, UK",
                ),
                booking_type="hotel",
                booking_source=BookingSourceEnum.MOBILE_APP,
                booking_created_date=datetime.now(tz=timezone.utc),
                booking_currency="USD",
                booking_amount=150.0,
                travel_from_date=datetime(2024, 8, 1, tzinfo=timezone.utc),
                travel_to_date=datetime(2024, 8, 10, tzinfo=timezone.utc),
                travel_from_location="London, UK",
                travel_to_location="Paris, France",
                booking_status=BookingStatusEnum.CANCELLED,
                booking_transaction_reference="txn_67890",
            ),
            payment=PaymentsLineItem(
                payment_id="p2",
                payment_method=PaymentMethodEnum.CREDIT_CARD,
                payment_source=PaymentSourceEnum.STRIPE,
                customer=UserListItem(
                    user_id="2",
                    user_first_name="Jane",
                    user_last_name="Smith",
                    user_email="jane.smith@example.com",
                    user_registration_date=datetime.now(tz=timezone.utc),
                    user_is_active=False,
                    user_tier=UserTierEnum.AUREA,
                    user_phone_number="+0987654321",
                    user_base_location="London, UK",
                ),
                booking_id="b2",
                payment_date=datetime.now(tz=timezone.utc),
                payment_currency="USD",
                payment_amount=150.0,
                payment_transaction_reference="txn_67890",
                payment_status=PaymentStatusEnum.REFUNDED,
            ),
            refund_date=datetime.now(tz=timezone.utc),
            payment_currency="USD",
            payment_amount=150.0,
            payment_transaction_reference="txn_67890",
            payment_status=PaymentStatusEnum.REFUNDED,
        ),
    )


@customer_router.post(
    "/pricing-offers-discounts/list",
    response_model=ApiSuccessResponse[PaginatedResult[OfferLineItem]],
    status_code=200,
    summary="List pricing, offers and discounts for all customers with pagination and filtering",
    name="List Customer Pricing, Offers & Discounts",
)
async def list_customer_pricing_offers_discounts(
    query: PaginationParams = Query(...),
) -> ApiSuccessResponse[PaginatedResult[OfferLineItem]]:
    """
    List pricing, offers and discounts for all customers with pagination
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=20,  # Replace with actual total count from database
            page=query.page,
            size=query.size,
            items=[
                OfferLineItem(
                    offer_id="o1",
                    offer_type="discount",
                    offer_is_active=True,
                    offer_title="Summer Sale",
                    offer_description="Get 20% off on all bookings made in June!",
                    offer_valid_from=datetime(2024, 6, 1, tzinfo=timezone.utc),
                    offer_valid_to=datetime(2024, 6, 30, tzinfo=timezone.utc),
                ),  # Replace with actual pricing/offer/discount models
                OfferLineItem(
                    offer_id="o2",
                    offer_type="offer",
                    offer_is_active=False,
                    offer_title="Early Bird Offer",
                    offer_description="Book 30 days in advance and get 15% off!",
                    offer_valid_from=datetime(2024, 5, 1, tzinfo=timezone.utc),
                    offer_valid_to=datetime(2024, 5, 31, tzinfo=timezone.utc),
                ),
            ],
        ),
    )


@customer_router.post(
    "/support-tickets/list",
    response_model=ApiSuccessResponse[PaginatedResult[SupportTicketLineItem]],
    status_code=200,
    summary="List support tickets for all customers with pagination and filtering",
    name="List Customer Support Tickets",
)
async def list_customer_support_tickets(
    query: PaginationParams = Query(...),
) -> ApiSuccessResponse[PaginatedResult[SupportTicketLineItem]]:
    """
    List support tickets for all customers with pagination
    """

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult(
            total=10,  # Replace with actual total count from database
            page=query.page,
            size=query.size,
            items=[
                SupportTicketLineItem(
                    ticket_id="t1",
                    customer=UserListItem(
                        user_id="1",
                        user_first_name="John",
                        user_last_name="Doe",
                        user_email="john.doe@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=True,
                        user_tier=UserTierEnum.NOVUS,
                        user_phone_number="+1234567890",
                        user_base_location="New York, USA",
                    ),
                    booking_id="b1",
                    ticket_created_date=datetime.now(tz=timezone.utc),
                    ticket_status="open",
                    ticket_subject="Issue with booking",
                    ticket_description="I have an issue with my recent booking. Please assist.",
                    ticket_resolution_date=None,
                    ticket_resolution_details=None,
                    ticket_priority=SupportTicketPriorityEnum.HIGH,
                    assigned_agent=AgentDetailModel(
                        agent_id="a1",
                        agent_first_name="Alice",
                        agent_last_name="Johnson",
                        agent_email="alice.johnson@example.com",
                        agent_phone_number="+1234567890",
                    ),
                ),  # Replace with actual support ticket models
                SupportTicketLineItem(
                    ticket_id="t2",
                    customer=UserListItem(
                        user_id="2",
                        user_first_name="Jane",
                        user_last_name="Smith",
                        user_email="jane.smith@example.com",
                        user_registration_date=datetime.now(tz=timezone.utc),
                        user_is_active=False,
                        user_tier=UserTierEnum.AUREA,
                        user_phone_number="+0987654321",
                        user_base_location="London, UK",
                    ),
                    booking_id=None,
                    ticket_created_date=datetime.now(tz=timezone.utc),
                    ticket_status="closed",
                    ticket_subject="Refund request",
                    ticket_description="I would like to request a refund for my last booking.",
                    ticket_resolution_date=datetime.now(tz=timezone.utc),
                    ticket_resolution_details="Refund processed successfully. Amount will be credited to your account within 5-7 business days.",
                    ticket_priority=SupportTicketPriorityEnum.MEDIUM,
                    assigned_agent=AgentDetailModel(
                        agent_id="a2",
                        agent_first_name="Bob",
                        agent_last_name="Smith",
                        agent_email="bob.smith@example.com",
                        agent_phone_number="+0987654321",
                    ),
                ),
            ],
        ),
    )
