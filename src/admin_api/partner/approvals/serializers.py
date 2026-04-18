from pydantic import AwareDatetime

from admin_api.partner.approvals.domainmodel import (
    ApprovalContentDetailsDomainModel,
    ApprovalKycDetailsDomainModel,
    ApprovalLineItemDomainModel,
    ApprovalStatusEnum,
    ApprovalSummaryDomainModel,
    ApprovalTypeEnum,
    LifetimeApprovalSummaryDomainModel,
)
from admin_api.partner.approvals.dto import ApprovalActionDTO
from common.serializerlib import (
    ApiSerializerBaseModel,
    BankDetailsSerializer,
    ImageMetadataSerializer,
)


class ApprovalSummary(ApiSerializerBaseModel):
    pending_approvals: int
    kyc_pending: int
    content_updates: int
    new_partners: int

    @classmethod
    def from_domain_model(cls, domain_model: ApprovalSummaryDomainModel) -> ApprovalSummary:
        return cls(
            pending_approvals=domain_model.pending_approvals,
            kyc_pending=domain_model.kyc_pending,
            content_updates=domain_model.content_updates,
            new_partners=domain_model.new_partners,
        )


class LifetimeApprovalSummary(ApiSerializerBaseModel):
    property_approvals: int
    activity_approvals: int
    b2b_agents: int
    affiliates: int
    content_updates: int
    kyc_approvals: int

    @classmethod
    def from_domain_model(
        cls, domain_model: LifetimeApprovalSummaryDomainModel
    ) -> LifetimeApprovalSummary:
        return cls(
            property_approvals=domain_model.property_approvals,
            activity_approvals=domain_model.activity_approvals,
            b2b_agents=domain_model.b2b_agents,
            affiliates=domain_model.affiliates,
            content_updates=domain_model.content_updates,
            kyc_approvals=domain_model.kyc_approvals,
        )


class ApprovalLineItem(ApiSerializerBaseModel):
    approval_id: str
    approval_type: ApprovalTypeEnum
    name: str
    submitted_by: str
    date: AwareDatetime
    status: ApprovalStatusEnum

    @classmethod
    def from_domain_model(cls, domain_model: ApprovalLineItemDomainModel) -> ApprovalLineItem:
        return cls(
            approval_id=domain_model.approval_id,
            approval_type=domain_model.approval_type,
            name=domain_model.name,
            submitted_by=domain_model.submitted_by,
            date=domain_model.submitted_on,
            status=domain_model.status,
        )


class ApprovalKycDetails(ApiSerializerBaseModel):
    partner_id: str
    partner_name: str
    partner_email: str
    phone_number: str
    pan_number: str
    gst_number: str
    bank_details: BankDetailsSerializer
    kyc_documents: list[ImageMetadataSerializer]

    @classmethod
    def from_domain_model(cls, domain_model: ApprovalKycDetailsDomainModel) -> ApprovalKycDetails:
        return cls(
            partner_id=domain_model.partner_id,
            partner_name=domain_model.partner_name,
            partner_email=domain_model.partner_email,
            phone_number=domain_model.phone_number,
            pan_number=domain_model.pan_number,
            gst_number=domain_model.gst_number,
            bank_details=BankDetailsSerializer(
                account_holder_name=domain_model.bank_account_holder_name,
                account_number=domain_model.bank_account_number,
                ifsc_code=domain_model.bank_ifsc_code,
                bank_name=domain_model.bank_name,
            ),
            kyc_documents=[
                ImageMetadataSerializer(
                    luxtj_id=doc.luxtj_id,
                    url=doc.url,
                    image_size_bytes=doc.image_size_bytes,
                    mime_type=doc.mime_type,
                    alt_text=doc.alt_text,
                )
                for doc in domain_model.kyc_documents
            ],
        )


class ApprovalActionBody(ApiSerializerBaseModel):
    comment: str | None = None

    def to_dto(self) -> ApprovalActionDTO:
        return ApprovalActionDTO(comment=self.comment)


class ApprovalContentDetails(ApiSerializerBaseModel):
    content_id: str
    name: str
    description: str | None
    images: list[ImageMetadataSerializer]

    @classmethod
    def from_domain_model(
        cls, domain_model: ApprovalContentDetailsDomainModel
    ) -> ApprovalContentDetails:
        return cls(
            content_id=domain_model.content_id,
            name=domain_model.title,
            description=domain_model.description,
            images=[
                ImageMetadataSerializer(
                    luxtj_id=doc.luxtj_id,
                    url=doc.url,
                    image_size_bytes=doc.image_size_bytes,
                    mime_type=doc.mime_type,
                    alt_text=doc.alt_text,
                )
                for doc in domain_model.content_images
            ],
        )
