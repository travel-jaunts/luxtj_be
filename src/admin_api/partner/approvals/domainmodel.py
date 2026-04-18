from dataclasses import dataclass
from datetime import datetime

from luxtj.domain.enums import ApprovalStatusEnum, ApprovalTypeEnum
from luxtj.utils import mockutils


@dataclass
class ApprovalSummaryDomainModel:
    pending_approvals: int
    kyc_pending: int
    content_updates: int
    new_partners: int

    @classmethod
    def generate_mock(cls) -> ApprovalSummaryDomainModel:
        return cls(
            pending_approvals=mockutils.random.randint(10, 80),
            kyc_pending=mockutils.random.randint(3, 30),
            content_updates=mockutils.random.randint(2, 25),
            new_partners=mockutils.random.randint(1, 20),
        )


@dataclass
class LifetimeApprovalSummaryDomainModel:
    property_approvals: int
    activity_approvals: int
    b2b_agents: int
    affiliates: int
    content_updates: int
    kyc_approvals: int

    @classmethod
    def generate_mock(cls) -> LifetimeApprovalSummaryDomainModel:
        return cls(
            property_approvals=mockutils.random.randint(100, 700),
            activity_approvals=mockutils.random.randint(80, 500),
            b2b_agents=mockutils.random.randint(40, 200),
            affiliates=mockutils.random.randint(40, 220),
            content_updates=mockutils.random.randint(20, 300),
            kyc_approvals=mockutils.random.randint(100, 700),
        )


@dataclass
class ApprovalLineItemDomainModel:
    approval_id: str
    approval_type: ApprovalTypeEnum
    name: str
    submitted_by: str
    submitted_on: datetime
    status: ApprovalStatusEnum

    @classmethod
    def generate_mock(cls) -> ApprovalLineItemDomainModel:
        entity_type = mockutils.random.choice(list(ApprovalTypeEnum))
        entity_name = (
            mockutils.random_property_name()
            if entity_type == ApprovalTypeEnum.CONTENT
            else f"{mockutils.random_user_last_name()} {entity_type.value.replace('_', ' ').title()}"
        )
        return cls(
            approval_id=mockutils.random_booking_id(),
            approval_type=entity_type,
            name=entity_name,
            submitted_by=mockutils.random_user_email(),
            submitted_on=mockutils.random_date_from_past_days(),
            status=mockutils.random.choice(list(ApprovalStatusEnum)),
        )


@dataclass
class ContentImageDomainModel:
    luxtj_id: str
    url: str
    image_size_bytes: int
    mime_type: str
    alt_text: str | None

    @classmethod
    def generate_mock(cls) -> ContentImageDomainModel:
        return cls(
            luxtj_id=mockutils.random_booking_id(),
            url="https://example.com/mock-image.jpg",
            image_size_bytes=mockutils.random.randint(50000, 500000),
            mime_type="image/jpeg",
            alt_text="Mock Property Image",
        )


@dataclass
class ApprovalKycDetailsDomainModel:
    partner_id: str
    partner_name: str
    partner_email: str
    phone_number: str
    pan_number: str
    gst_number: str
    bank_account_holder_name: str
    bank_account_number: str
    bank_ifsc_code: str
    bank_name: str
    kyc_documents: list[ContentImageDomainModel]

    @classmethod
    def generate_mock(cls) -> ApprovalKycDetailsDomainModel:
        return cls(
            partner_id=mockutils.random_user_id(),
            partner_name=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            partner_email=mockutils.random_user_email(),
            phone_number=mockutils.random_user_phone_number(),
            pan_number="ABCDE1234F",
            gst_number="22ABCDE1234F1Z5",
            bank_account_holder_name=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            bank_account_number=str(mockutils.random.randint(100000000000, 999999999999)),
            bank_ifsc_code="MOCK0001234",
            bank_name="Mock Bank",
            kyc_documents=[
                ContentImageDomainModel.generate_mock()
                for _ in range(mockutils.random.randint(1, 3))
            ],
        )


@dataclass
class ApprovalContentDetailsDomainModel:
    content_id: str
    title: str
    description: str
    content_images: list[ContentImageDomainModel]

    @classmethod
    def generate_mock(cls) -> ApprovalContentDetailsDomainModel:
        return cls(
            content_id=mockutils.random_booking_id(),
            title="Mock Property Title",
            description="This is a mock description for the property/activity pending approval.",
            content_images=[
                ContentImageDomainModel.generate_mock()
                for _ in range(mockutils.random.randint(1, 5))
            ],
        )
