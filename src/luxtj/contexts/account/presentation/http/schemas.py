from pydantic import Field

from luxtj.contexts.account.application.use_cases import AuthTokenPairDTO
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class RequestOtpBody(ApiSerializerBaseModel):
    dial_code: str = Field(..., min_length=1, max_length=8)
    phone_number: str = Field(..., min_length=1, max_length=32)
    email: str | None = Field(None, max_length=320)


class VerifyOtpBody(ApiSerializerBaseModel):
    dial_code: str = Field(..., min_length=1, max_length=8)
    phone_number: str = Field(..., min_length=1, max_length=32)
    otp: str = Field(..., min_length=4, max_length=12)
    email: str | None = Field(None, max_length=320)


class RequestOtpResultSerializer(ApiSerializerBaseModel):
    message: str


class TokenPairSerializer(ApiSerializerBaseModel):
    access_token: str
    refresh_token: str

    @classmethod
    def from_dto(cls, dto: AuthTokenPairDTO) -> TokenPairSerializer:
        return cls(
            access_token=dto.access_token,
            refresh_token=dto.refresh_token,
        )
