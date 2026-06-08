from uuid import UUID

from pydantic import Field

from luxtj.contexts.acquisition.application.use_cases import WaitlistEntryDTO
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class RegisterWaitlistEntryBody(ApiSerializerBaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Registrant's full name")
    email: str = Field(..., description="Registrant's email address")
    source: str | None = Field(
        None,
        max_length=128,
        description="Page or surface where the signup occurred (e.g. 'landing_page', 'blog_cta')",
    )
    referral_code: str | None = Field(
        None, max_length=128, description="Referral code if the registrant was referred"
    )


class WaitlistEntrySerializer(ApiSerializerBaseModel):
    id: UUID
    name: str
    email: str
    status: str

    @classmethod
    def from_dto(cls, dto: WaitlistEntryDTO) -> WaitlistEntrySerializer:
        return cls(id=dto.id, name=dto.name, email=dto.email, status=dto.status)
