from admin_api.partner.affiliate.domainmodel import (
    AffiliatePartnerBizKpiSummaryDomainModel,
    AffiliatePartnerDetailsDomainModel,
    AffiliatePartnerDomainModel,
    AffiliatePartnerStatusEnum,
)
from admin_api.partner.affiliate.dto import UpdateAffiliatePartnerDetailsDTO
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel


class AffiliatePartnerBizKpiSummary(ApiSerializerBaseModel):
    total_affiliates: int
    number_active: int
    number_pending: int
    earnings: AmountSerializer

    @classmethod
    def from_domain_model(
        cls, domain_model: AffiliatePartnerBizKpiSummaryDomainModel
    ) -> AffiliatePartnerBizKpiSummary:
        return cls(
            total_affiliates=domain_model.total_affiliates,
            number_active=domain_model.number_active,
            number_pending=domain_model.number_pending,
            earnings=AmountSerializer(
                amount=domain_model.earnings_amount,
                currency=domain_model.earnings_currency,
            ),
        )


class AffiliatePartnerLineItem(ApiSerializerBaseModel):
    partner_id: str
    affiliate_name: str
    platform: str
    traffic: int
    commission: float
    earnings: AmountSerializer
    status: AffiliatePartnerStatusEnum

    @classmethod
    def from_domain_model(
        cls, domain_model: AffiliatePartnerDomainModel
    ) -> AffiliatePartnerLineItem:
        return cls(
            partner_id=domain_model.partner_id,
            affiliate_name=domain_model.affiliate_name,
            platform=domain_model.platform,
            traffic=domain_model.traffic,
            commission=domain_model.commission_percent,
            earnings=AmountSerializer(
                amount=domain_model.earnings_amount,
                currency=domain_model.earnings_currency,
            ),
            status=domain_model.status,
        )


class AffiliatePartnerDetails(ApiSerializerBaseModel):
    partner_id: str

    name: str
    website: str
    social_media: str
    contact: str

    affiliate_link: str
    clicks: int
    bookings: int
    revenue: AmountSerializer
    commission_percent: float

    payments_paid: AmountSerializer
    payments_pending: AmountSerializer

    @classmethod
    def from_domain_model(
        cls, domain_model: AffiliatePartnerDetailsDomainModel
    ) -> AffiliatePartnerDetails:
        return cls(
            partner_id=domain_model.partner_id,
            name=domain_model.name,
            website=domain_model.website,
            social_media=domain_model.social_media,
            contact=domain_model.contact,
            affiliate_link=domain_model.affiliate_link,
            clicks=domain_model.clicks,
            bookings=domain_model.bookings,
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.revenue_currency,
            ),
            commission_percent=domain_model.commission_percent,
            payments_paid=AmountSerializer(
                amount=domain_model.payments_paid_amount,
                currency=domain_model.payments_currency,
            ),
            payments_pending=AmountSerializer(
                amount=domain_model.payments_pending_amount,
                currency=domain_model.payments_currency,
            ),
        )


class UpdateAffiliatePartnerDetailsBody(ApiSerializerBaseModel):
    name: str
    website: str
    social_media: str
    contact: str
    affiliate_link: str
    commission_percent: float

    def to_dto(self) -> UpdateAffiliatePartnerDetailsDTO:
        return UpdateAffiliatePartnerDetailsDTO(
            name=self.name,
            website=self.website,
            social_media=self.social_media,
            contact=self.contact,
            affiliate_link=self.affiliate_link,
            commission_percent=self.commission_percent,
        )
