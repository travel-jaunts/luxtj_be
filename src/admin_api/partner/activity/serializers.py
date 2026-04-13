from pydantic import AwareDatetime

from admin_api.partner.activity.domainmodel import (
    ActivityPartnerBizKpiSummaryDomainModel,
    ActivityPartnerDetailsDomainModel,
    ActivityPartnerDomainModel,
    ActivityPartnerStatusEnum,
)
from admin_api.partner.activity.dto import UpdateActivityPartnerDetailsDTO
from common.serializerlib import (
    AmountSerializer,
    ApiSerializerBaseModel,
    BankDetailsSerializer,
    ImageMetadataSerializer,
)
from luxtj.domain.enums import PartnerKYCStatusEnum


class ActivityPartnerBizKpiSummary(ApiSerializerBaseModel):
    total_activity_partners: int
    number_active: int
    number_pending: int
    number_suspended: int
    number_kyc_pending: int

    @classmethod
    def from_domain_model(
        cls, domain_model: ActivityPartnerBizKpiSummaryDomainModel
    ) -> ActivityPartnerBizKpiSummary:
        return cls(
            total_activity_partners=domain_model.total_activity_partners,
            number_active=domain_model.number_active,
            number_pending=domain_model.number_pending,
            number_suspended=domain_model.number_suspended,
            number_kyc_pending=domain_model.number_kyc_pending,
        )


class ActivityPartnerLineItem(ApiSerializerBaseModel):
    partner_id: str
    activity_name: str
    partner_name: str
    location: str
    activity_type: str
    status: ActivityPartnerStatusEnum
    kyc_status: PartnerKYCStatusEnum
    last_updated: AwareDatetime

    @classmethod
    def from_domain_model(cls, domain_model: ActivityPartnerDomainModel) -> ActivityPartnerLineItem:
        return cls(
            partner_id=domain_model.partner_id,
            activity_name=domain_model.activity_name,
            partner_name=domain_model.partner_name,
            location=domain_model.location,
            activity_type=domain_model.activity_type,
            status=domain_model.status,
            kyc_status=domain_model.kyc_status,
            last_updated=domain_model.last_updated,
        )


class ActivityPartnerDetails(ApiSerializerBaseModel):
    partner_id: str

    company_name: str
    contact_person: str
    phone: str
    email: str

    activities: list[str]

    per_person_price: AmountSerializer
    group_price: AmountSerializer
    seasonal_price: AmountSerializer

    open_months_weeks_days: str
    timings: str
    capacity: int

    license_document: ImageMetadataSerializer
    insurance_document: ImageMetadataSerializer
    bank_details: BankDetailsSerializer

    @classmethod
    def from_domain_model(
        cls, domain_model: ActivityPartnerDetailsDomainModel
    ) -> ActivityPartnerDetails:
        return cls(
            partner_id=domain_model.partner_id,
            company_name=domain_model.company_name,
            contact_person=domain_model.contact_person,
            phone=domain_model.phone,
            email=domain_model.email,
            activities=domain_model.activities,
            per_person_price=AmountSerializer(
                amount=domain_model.per_person_price.amount,
                currency=domain_model.per_person_price.currency,
            ),
            group_price=AmountSerializer(
                amount=domain_model.group_price.amount,
                currency=domain_model.group_price.currency,
            ),
            seasonal_price=AmountSerializer(
                amount=domain_model.seasonal_price.amount,
                currency=domain_model.seasonal_price.currency,
            ),
            open_months_weeks_days=domain_model.open_months_weeks_days,
            timings=domain_model.timings,
            capacity=domain_model.capacity,
            license_document=ImageMetadataSerializer(
                luxtj_id=domain_model.license_document.luxtj_id,
                url=domain_model.license_document.url,
                image_size_bytes=domain_model.license_document.image_size_bytes,
                mime_type=domain_model.license_document.mime_type,
                alt_text=domain_model.license_document.alt_text,
            ),
            insurance_document=ImageMetadataSerializer(
                luxtj_id=domain_model.insurance_document.luxtj_id,
                url=domain_model.insurance_document.url,
                image_size_bytes=domain_model.insurance_document.image_size_bytes,
                mime_type=domain_model.insurance_document.mime_type,
                alt_text=domain_model.insurance_document.alt_text,
            ),
            bank_details=BankDetailsSerializer(
                account_holder_name=domain_model.bank_details.account_holder_name,
                account_number=domain_model.bank_details.account_number,
                ifsc_code=domain_model.bank_details.ifsc_code,
                bank_name=domain_model.bank_details.bank_name,
            ),
        )


class UpdateActivityPartnerDetailsBody(ApiSerializerBaseModel):
    company_name: str
    contact_person: str
    phone: str
    email: str
    activities: list[str]
    per_person_price: AmountSerializer
    group_price: AmountSerializer
    seasonal_price: AmountSerializer
    open_months_weeks_days: str
    timings: str
    capacity: int

    def to_dto(self) -> UpdateActivityPartnerDetailsDTO:
        return UpdateActivityPartnerDetailsDTO(
            company_name=self.company_name,
            contact_person=self.contact_person,
            phone=self.phone,
            email=self.email,
            activities=self.activities,
            per_person_price_amount=self.per_person_price.amount,
            per_person_price_currency=self.per_person_price.currency,
            group_price_amount=self.group_price.amount,
            group_price_currency=self.group_price.currency,
            seasonal_price_amount=self.seasonal_price.amount,
            seasonal_price_currency=self.seasonal_price.currency,
            open_months_weeks_days=self.open_months_weeks_days,
            timings=self.timings,
            capacity=self.capacity,
        )
