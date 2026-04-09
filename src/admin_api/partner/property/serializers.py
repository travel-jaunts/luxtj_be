from pydantic import AwareDatetime

from admin_api.partner.property.domainmodel import (
    PartnerBizKpiSummaryDomainModel,
    PropertyPartnerDomainModel,
)
from admin_api.partner.offers.serializers import PartnerOfferDetailLineItem
from common.serializerlib import ApiSerializerBaseModel, ImageMetadataSerializer, AmountSerializer, LocationMetadataSerializer, BankDetailsSerializer
from luxtj.domain.enums import PartnerKYCStatusEnum, PropertySourceEnum, PropertyStatusEnum


class PartnerBizKpiSummary(ApiSerializerBaseModel):
    total_property_partners: int
    number_active: int
    number_pending_approval: int
    number_rejected: int
    number_suspended: int
    number_kyc_pending: int

    @classmethod
    def from_domain_model(
        cls, biz_summary_model: PartnerBizKpiSummaryDomainModel
    ) -> PartnerBizKpiSummary:
        return cls(
            total_property_partners=biz_summary_model.total_property_partners,
            number_active=biz_summary_model.number_active,
            number_pending_approval=biz_summary_model.number_pending_approval,
            number_rejected=biz_summary_model.number_rejected,
            number_suspended=biz_summary_model.number_suspended,
            number_kyc_pending=biz_summary_model.number_kyc_pending,
        )


class PropertyPartnerLineItem(ApiSerializerBaseModel):
    partner_id: str
    partner_email: str
    property_name: str
    property_location: str
    property_type: str
    property_source: PropertySourceEnum
    property_status: PropertyStatusEnum
    partner_kyc_status: PartnerKYCStatusEnum
    property_room_count: int
    last_updated: AwareDatetime

    @classmethod
    def from_domain_model(cls, domain_model: PropertyPartnerDomainModel) -> PropertyPartnerLineItem:
        return cls(
            partner_id=domain_model.property_partner_id,
            partner_email=domain_model.property_partner_email,
            property_name=domain_model.property_name,
            property_location=domain_model.property_location,
            property_type=domain_model.property_type,
            property_source=domain_model.property_source,
            property_status=domain_model.property_status,
            partner_kyc_status=domain_model.partner_kyc_status,
            property_room_count=domain_model.property_room_count,
            last_updated=domain_model.last_updated,
        )


class PropertyPartnerDetails(ApiSerializerBaseModel):
    # basic info
    partner_id: str
    property_name: str
    property_owner_name: str
    property_contact_number: str
    partner_email: str
    property_address: str

    # content
    property_images: list[ImageMetadataSerializer]
    property_room_types: list[str]
    property_amenities: list[str]
    property_description: str
    property_location: LocationMetadataSerializer

    # pricing
    property_base_price: AmountSerializer
    seasonal_prices: AmountSerializer
    offers: list[PartnerOfferDetailLineItem]

    # kyc
    partner_pan_number: str
    partner_gst_number: str
    partner_bank: BankDetailsSerializer
    kyc_documents: list[ImageMetadataSerializer]
