from enum import StrEnum

from pydantic import BaseModel


class RequestProcessStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class BaseResponse(BaseModel):
    status: RequestProcessStatus


class ErrorResponse(BaseResponse):
    errorMessage: str

class SuccessResponse(BaseResponse):
    output: BaseModel | None = None
