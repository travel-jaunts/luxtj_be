from pydantic import AwareDatetime

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
    offer_status: OfferTypeEnum
    offer_type: OfferStatusEnum
