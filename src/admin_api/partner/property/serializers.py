from pydantic import AwareDatetime

from admin_api.partner.offers.serializers import PartnerOfferDetailLineItem
from admin_api.partner.property.domainmodel import (
    PartnerBizKpiSummaryDomainModel,
    PropertyPartnerDetailsDomainModel,
    PropertyPartnerDomainModel,
)
from admin_api.partner.property.dto import UpdatePropertyPartnerDetailsDTO
from common.serializerlib import (
    AmountSerializer,
    ApiSerializerBaseModel,
    BankDetailsSerializer,
    ImageMetadataSerializer,
    LocationMetadataSerializer,
)
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

    @classmethod
    def from_domain_model(
        cls, domain_model: PropertyPartnerDetailsDomainModel
    ) -> PropertyPartnerDetails:
        return cls(
            partner_id=domain_model.partner_id,
            property_name=domain_model.property_name,
            property_owner_name=domain_model.property_owner_name,
            property_contact_number=domain_model.property_contact_number,
            partner_email=domain_model.partner_email,
            property_address=domain_model.property_address,
            property_images=[
                ImageMetadataSerializer(
                    luxtj_id=img.luxtj_id,
                    url=img.url,
                    image_size_bytes=img.image_size_bytes,
                    mime_type=img.mime_type,
                    alt_text=img.alt_text,
                )
                for img in domain_model.property_images
            ],
            property_room_types=domain_model.property_room_types,
            property_amenities=domain_model.property_amenities,
            property_description=domain_model.property_description,
            property_location=LocationMetadataSerializer(
                latitude=domain_model.property_location.latitude,
                longitude=domain_model.property_location.longitude,
                address_line1=domain_model.property_location.address_line1,
                address_line2=domain_model.property_location.address_line2,
                city=domain_model.property_location.city,
                state=domain_model.property_location.state,
                postal_code=domain_model.property_location.postal_code,
                country=domain_model.property_location.country,
            ),
            property_base_price=AmountSerializer(
                amount=domain_model.property_base_price_amount,
                currency=domain_model.property_base_price_currency,
            ),
            seasonal_prices=AmountSerializer(
                amount=domain_model.seasonal_price_amount,
                currency=domain_model.seasonal_price_currency,
            ),
            offers=[],  # TODO: populate from domain model when offer details are implemented
            partner_pan_number=domain_model.partner_pan_number,
            partner_gst_number=domain_model.partner_gst_number,
            partner_bank=BankDetailsSerializer(
                account_holder_name=domain_model.partner_bank.account_holder_name,
                account_number=domain_model.partner_bank.account_number,
                ifsc_code=domain_model.partner_bank.ifsc_code,
                bank_name=domain_model.partner_bank.bank_name,
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


class UpdatePropertyPartnerDetailsBody(ApiSerializerBaseModel):
    property_name: str
    property_owner_name: str
    property_contact_number: str
    partner_email: str
    property_address: str
    property_amenities: list[str]
    property_description: str
    property_room_types: list[str]
    property_base_price: AmountSerializer
    property_location: LocationMetadataSerializer

    def to_dto(self) -> UpdatePropertyPartnerDetailsDTO:
        return UpdatePropertyPartnerDetailsDTO(
            property_name=self.property_name,
            property_owner_name=self.property_owner_name,
            property_contact_number=self.property_contact_number,
            partner_email=self.partner_email,
            property_address=self.property_address,
            property_amenities=self.property_amenities,
            property_description=self.property_description,
            property_room_types=self.property_room_types,
            property_base_price_amount=self.property_base_price.amount,
            property_base_price_currency=self.property_base_price.currency,
            location_latitude=self.property_location.latitude,
            location_longitude=self.property_location.longitude,
            location_address_line1=self.property_location.address_line1,
            location_address_line2=self.property_location.address_line2,
            location_city=self.property_location.city,
            location_state=self.property_location.state,
            location_postal_code=self.property_location.postal_code,
            location_country=self.property_location.country,
        )
