from datetime import date
from enum import StrEnum
from typing import Annotated, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

GenericResponseModel = TypeVar("GenericResponseModel", bound=BaseModel)


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.capitalize() for x in components[1:])


class ApiSerializerBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


# query models ------------------------------------------------------------------------------------
class PaginationParams(ApiSerializerBaseModel):
    page: int = Field(1, description="Page number")
    size: int = Field(10, description="Number of items per page")


class SearchFilterParams(ApiSerializerBaseModel):
    search_query: str | None = Field(None, alias="q", description="Search query to filter results")
    from_date: date | None = Field(None, description="Start date for filtering results (inclusive)")
    to_date: date | None = Field(None, description="End date for filtering results (inclusive)")


# response models ---------------------------------------------------------------------------------
class RequestProcessStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class ApiResponse(ApiSerializerBaseModel):
    status: RequestProcessStatus


class ApiSuccessResponse[GenericResponseModel](ApiResponse):
    status: RequestProcessStatus = RequestProcessStatus.OK
    output: GenericResponseModel | None = None


class ApiErrorResponse(ApiResponse):
    status: RequestProcessStatus = RequestProcessStatus.ERROR
    error_message: str


class HealthStatusResult(ApiSerializerBaseModel):
    uptime_seconds: int = Field(..., description="Uptime of the application in seconds")
    database_connected: bool = Field(
        ..., description="Whether the application is connected to the database"
    )


class PaginatedResult[GenericResponseModel](ApiSerializerBaseModel):
    total: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    items: list[GenericResponseModel] = Field(
        ..., description="List of elements for the current page"
    )


# common serializers ------------------------------------------------------------------------------
class AmountSerializer(ApiSerializerBaseModel):
    amount: float = Field(..., description="Monetary amount")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")


class ImageMetadataSerializer(ApiSerializerBaseModel):
    luxtj_id: str = Field(..., description="Unique identifier for the image in the Luxtj system")
    url: str = Field(..., description="URL of the image")
    image_size_bytes: int = Field(..., description="Size of the image in bytes")
    mime_type: str = Field(..., description="MIME type of the image (e.g., image/jpeg, image/png)")
    alt_text: str | None = Field(..., description="Alternative text for the image")


class LocationMetadataSerializer(ApiSerializerBaseModel):
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    address_line1: str = Field(..., description="First line of the address")
    address_line2: str | None = Field(..., description="Second line of the address (optional)")
    city: str = Field(..., description="City of the location")
    state: str = Field(..., description="State or province of the location")
    postal_code: str = Field(..., description="Postal code of the location")
    country: str = Field(..., description="Country of the location")


class BankDetailsSerializer(ApiSerializerBaseModel):
    account_holder_name: str = Field(..., description="Name of the bank account holder")
    account_number: str = Field(..., description="Bank account number")
    ifsc_code: str = Field(..., description="IFSC code of the bank branch")
    bank_name: str = Field(..., description="Name of the bank")


# common query parameters -------------------------------------------------------------------------
CurrencyQuery = Annotated[
    str,
    Query(
        ...,
        alias="currency",
        description="ISO currency code for the KPI summary (e.g., USD, EUR)",
    ),
]
"""Query parameter for specifying the ISO currency code in API requests that require it (e.g., for KPI summaries)."""
