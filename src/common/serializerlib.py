from typing import TypeVar, Annotated
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from fastapi import Query

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
    search_query: str | None = Field(None, alias="q", description="Search query to filter results")


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


# common query parameters -------------------------------------------------------------------------
CurrencyQuery = Annotated[
    str,
    Query(
        ...,
        alias="currency",
        description="ISO currency code for the KPI summary (e.g., USD, EUR)",
    ),
]
"""Query parameter for specifying the ISO currency code in API requests that require it 
(e.g., for KPI summaries)."""
