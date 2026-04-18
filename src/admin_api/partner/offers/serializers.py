from datetime import date

from pydantic import AwareDatetime

from admin_api.partner.offers.domainmodel import (
    OfferPricingActivityLineItemDomainModel,
    OfferPricingCommissionLineItemDomainModel,
    OfferPricingPropertyLineItemDomainModel,
    OfferPricingSeasonalLineItemDomainModel,
    OfferPricingSummaryDomainModel,
    PartnerOfferLineItemDomainModel,
)
from admin_api.partner.offers.dto import (
    CreatePartnerOfferDTO,
    UpdateActivityPricingDTO,
    UpdateCommissionDTO,
    UpdatePartnerOfferDTO,
    UpdatePropertyPricingDTO,
    UpdateSeasonalPricingDTO,
)
from common.serializerlib import AmountSerializer, ApiSerializerBaseModel
from luxtj.domain.enums import OfferStatusEnum, OfferTypeEnum


class PartnerOfferDetailLineItem(ApiSerializerBaseModel):
    offer_id: str
    offer_title: str
    property_id: str | None
    discount_percentage: float
    flat_discount: AmountSerializer
    valid_from: AwareDatetime
    valid_to: AwareDatetime
    minimun_booking: AmountSerializer
    minimum_nights: int
    offer_type: OfferTypeEnum
    offer_status: OfferStatusEnum


class OfferPricingSummary(ApiSerializerBaseModel):
    total_properties: int
    active_offers: int
    avg_commission_percentage: float
    seasonal_pricing_active: int

    @classmethod
    def from_domain_model(cls, domain_model: OfferPricingSummaryDomainModel) -> OfferPricingSummary:
        return cls(
            total_properties=domain_model.total_properties,
            active_offers=domain_model.active_offers,
            avg_commission_percentage=domain_model.avg_commission_percentage,
            seasonal_pricing_active=domain_model.seasonal_pricing_active,
        )


class PropertyPricingLineItem(ApiSerializerBaseModel):
    property_id: str
    property_name: str
    location: str
    base_price: AmountSerializer
    current_offer: str | None
    last_updated: AwareDatetime

    @classmethod
    def from_domain_model(
        cls, domain_model: OfferPricingPropertyLineItemDomainModel
    ) -> PropertyPricingLineItem:
        return cls(
            property_id=domain_model.property_id,
            property_name=domain_model.property_name,
            location=domain_model.location,
            base_price=AmountSerializer(
                amount=domain_model.base_price_amount,
                currency=domain_model.base_price_currency,
            ),
            current_offer=domain_model.current_offer,
            last_updated=domain_model.last_updated,
        )


class UpdatePropertyPricingBody(ApiSerializerBaseModel):
    base_price: AmountSerializer
    commission_percentage: float
    seasonal_price: AmountSerializer

    def to_dto(self) -> UpdatePropertyPricingDTO:
        return UpdatePropertyPricingDTO(
            base_price_amount=self.base_price.amount,
            base_price_currency=self.base_price.currency,
            commission_percentage=self.commission_percentage,
            seasonal_price_amount=self.seasonal_price.amount,
            seasonal_price_currency=self.seasonal_price.currency,
        )


class ActivityPricingLineItem(ApiSerializerBaseModel):
    activity_id: str
    activity_name: str
    location: str
    base_price: AmountSerializer
    offer: str | None
    commission_percentage: float

    @classmethod
    def from_domain_model(
        cls, domain_model: OfferPricingActivityLineItemDomainModel
    ) -> ActivityPricingLineItem:
        return cls(
            activity_id=domain_model.activity_id,
            activity_name=domain_model.activity_name,
            location=domain_model.location,
            base_price=AmountSerializer(
                amount=domain_model.base_price_amount,
                currency=domain_model.base_price_currency,
            ),
            offer=domain_model.offer,
            commission_percentage=domain_model.commission_percentage,
        )


class UpdateActivityPricingBody(ApiSerializerBaseModel):
    base_price: AmountSerializer
    commission_percentage: float
    seasonal_price: AmountSerializer

    def to_dto(self) -> UpdateActivityPricingDTO:
        return UpdateActivityPricingDTO(
            base_price_amount=self.base_price.amount,
            base_price_currency=self.base_price.currency,
            commission_percentage=self.commission_percentage,
            seasonal_price_amount=self.seasonal_price.amount,
            seasonal_price_currency=self.seasonal_price.currency,
        )


class CommissionLineItem(ApiSerializerBaseModel):
    commission_id: str
    partner_type: str
    commission_percentage: float
    last_updated: AwareDatetime

    @classmethod
    def from_domain_model(
        cls, domain_model: OfferPricingCommissionLineItemDomainModel
    ) -> CommissionLineItem:
        return cls(
            commission_id=domain_model.commission_id,
            partner_type=domain_model.partner_type,
            commission_percentage=domain_model.commission_percentage,
            last_updated=domain_model.last_updated,
        )


class UpdateCommissionBody(ApiSerializerBaseModel):
    commission_percentage: float

    def to_dto(self) -> UpdateCommissionDTO:
        return UpdateCommissionDTO(commission_percentage=self.commission_percentage)


class OfferLineItem(ApiSerializerBaseModel):
    offer_id: str
    offer_name: str
    applicable_to: str
    discount: str
    from_date: date
    to_date: date
    status: OfferStatusEnum

    @classmethod
    def from_domain_model(cls, domain_model: PartnerOfferLineItemDomainModel) -> OfferLineItem:
        if domain_model.discount_percentage is not None:
            discount = f"{domain_model.discount_percentage:.2f}%"
        elif domain_model.flat_discount_amount is not None:
            discount = (
                f"{domain_model.flat_discount_currency} "
                f"{domain_model.flat_discount_amount:.2f}"
            )
        else:
            discount = "-"

        return cls(
            offer_id=domain_model.offer_id,
            offer_name=domain_model.offer_name,
            applicable_to=domain_model.applicable_to,
            discount=discount,
            from_date=domain_model.start_date,
            to_date=domain_model.end_date,
            status=domain_model.status,
        )


class CreateOfferBody(ApiSerializerBaseModel):
    offer_name: str
    applicable_to: str
    applies_to_item: str
    discount_percentage: float | None = None
    flat_discount: AmountSerializer | None = None
    start_date: date
    end_date: date
    min_nights: int | None = None
    min_booking: AmountSerializer | None = None
    status: OfferStatusEnum

    def to_dto(self) -> CreatePartnerOfferDTO:
        return CreatePartnerOfferDTO(
            offer_name=self.offer_name,
            applicable_to=self.applicable_to,
            applies_to_item=self.applies_to_item,
            discount_percentage=self.discount_percentage,
            flat_discount_amount=self.flat_discount.amount if self.flat_discount else None,
            flat_discount_currency=self.flat_discount.currency if self.flat_discount else None,
            start_date=self.start_date,
            end_date=self.end_date,
            min_nights=self.min_nights,
            min_booking_amount=self.min_booking.amount if self.min_booking else None,
            min_booking_currency=self.min_booking.currency if self.min_booking else None,
            status=self.status,
        )


class UpdateOfferBody(ApiSerializerBaseModel):
    offer_name: str
    applicable_to: str
    applies_to_item: str
    discount_percentage: float | None = None
    flat_discount: AmountSerializer | None = None
    start_date: date
    end_date: date
    min_nights: int | None = None
    min_booking: AmountSerializer | None = None
    status: OfferStatusEnum

    def to_dto(self) -> UpdatePartnerOfferDTO:
        return UpdatePartnerOfferDTO(
            offer_name=self.offer_name,
            applicable_to=self.applicable_to,
            applies_to_item=self.applies_to_item,
            discount_percentage=self.discount_percentage,
            flat_discount_amount=self.flat_discount.amount if self.flat_discount else None,
            flat_discount_currency=self.flat_discount.currency if self.flat_discount else None,
            start_date=self.start_date,
            end_date=self.end_date,
            min_nights=self.min_nights,
            min_booking_amount=self.min_booking.amount if self.min_booking else None,
            min_booking_currency=self.min_booking.currency if self.min_booking else None,
            status=self.status,
        )


class SeasonalPricingLineItem(ApiSerializerBaseModel):
    seasonal_price_id: str
    property_name: str
    season: str
    price: AmountSerializer
    dates: str

    @classmethod
    def from_domain_model(
        cls, domain_model: OfferPricingSeasonalLineItemDomainModel
    ) -> SeasonalPricingLineItem:
        return cls(
            seasonal_price_id=domain_model.seasonal_price_id,
            property_name=domain_model.property_name,
            season=domain_model.season,
            price=AmountSerializer(
                amount=domain_model.price_amount,
                currency=domain_model.price_currency,
            ),
            dates=f"{domain_model.start_date.isoformat()} to {domain_model.end_date.isoformat()}",
        )


class UpdateSeasonalPricingBody(ApiSerializerBaseModel):
    property_name: str
    season: str
    price: AmountSerializer
    start_date: date
    end_date: date

    def to_dto(self) -> UpdateSeasonalPricingDTO:
        return UpdateSeasonalPricingDTO(
            property_name=self.property_name,
            season=self.season,
            price_amount=self.price.amount,
            price_currency=self.price.currency,
            start_date=self.start_date,
            end_date=self.end_date,
        )
