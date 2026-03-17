# Customers (B2C) (Main page to contain profiles) (a)
# - Bookings
# - Payments & Refunds
#     - Filtered Search, to slice and dice
# - Pricing, Offers & Discounts
#     - LuxTJ initiated discounts
# - Support (tickets & Complaints)

from datetime import datetime, timezone
from typing import TypeVar

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

from app.core.response_models import RequestProcessStatus


GenericResponseModel = TypeVar("GenericResponseModel", bound=BaseModel)


class ApiBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda s: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(s.split("_"))
        ),
        populate_by_name=True 
    )


# query modesl ------------------------------------------------------------------------------------
class PaginationParams(ApiBaseModel):
    page: int = Field(1, description="Page number")
    size: int = Field(10, description="Number of items per page")
    search_query: str | None = Field(None, alias="q", description="Search query to filter results")


# response models ---------------------------------------------------------------------------------
class ApiResponse(ApiBaseModel):
    status: RequestProcessStatus

    # TODO: add camel case alias generator for output field
    model_config = ConfigDict(
        alias_generator=lambda s: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(s.split("_"))
        ),
        populate_by_name=True 
    )


class ApiSuccessResponse[GenericResponseModel](ApiResponse):
    output: GenericResponseModel | None = None


class ApiErrorResponse(ApiResponse):
    error_message: str


class PaginatedResult[GenericResponseModel](ApiBaseModel):
    total: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    items: list[GenericResponseModel] = Field(
        ..., description="List of elements for the current page"
    )


# line item models --------------------------------------------------------------------------------
class UserListItem(ApiBaseModel):
    user_id: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_registration_date: AwareDatetime


class CustomerBookingLineItem(ApiBaseModel):
    booking_id: str
    customer_id: str
    booking_created_date: AwareDatetime
    booking_currency: str
    booking_amount: float
    booking_transaction_reference: str


class OfferLineItem(ApiBaseModel):
    offer_id: str
    offer_type: str
    offer_is_active: bool = Field(False, description="Indicates if the offer is currently active or not")
    offer_title: str
    offer_description: str
    offer_valid_from: AwareDatetime
    offer_valid_to: AwareDatetime | None

class SupportTicketLineItem(ApiBaseModel):
    ticket_id: str
    customer_id: str
    ticket_created_date: AwareDatetime
    ticket_status: str
    ticket_subject: str
    ticket_description: str

# =================================================================================================
customer_router = APIRouter(prefix="/customers", tags=["customers"])


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
                ),
                UserListItem(
                    user_id="2",
                    user_first_name="Jane",
                    user_last_name="Smith",
                    user_email="jane.smith@example.com",
                    user_registration_date=datetime.now(tz=timezone.utc),
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
                    customer_id="1",
                    booking_created_date=datetime.now(tz=timezone.utc),
                    booking_currency="USD",
                    booking_amount=100.0,
                    booking_transaction_reference="txn_12345",
                ),
                CustomerBookingLineItem(
                    booking_id="b2",
                    customer_id="2",
                    booking_created_date=datetime.now(tz=timezone.utc),
                    booking_currency="USD",
                    booking_amount=150.0,
                    booking_transaction_reference="txn_67890",
                ),
            ],
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
                    customer_id="1",
                    ticket_created_date=datetime.now(tz=timezone.utc),
                    ticket_status="open",
                    ticket_subject="Issue with booking",
                    ticket_description="I have an issue with my recent booking. Please assist.",
                ),  # Replace with actual support ticket models
                SupportTicketLineItem(
                    ticket_id="t2",
                    customer_id="2",
                    ticket_created_date=datetime.now(tz=timezone.utc),
                    ticket_status="closed",
                    ticket_subject="Refund request",
                    ticket_description="I would like to request a refund for my last booking.",
                ),
            ],
        ),
    )


admin_base_router = APIRouter(prefix="/admin")
admin_base_router.include_router(customer_router)
