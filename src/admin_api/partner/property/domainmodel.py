from dataclasses import dataclass
from datetime import datetime

from luxtj.domain.enums import PartnerKYCStatusEnum, PropertySourceEnum, PropertyStatusEnum
from luxtj.utils import mockutils


@dataclass
class PartnerBizKpiSummaryDomainModel:
    total_property_partners: int
    number_active: int
    number_pending_approval: int
    number_rejected: int
    number_suspended: int
    number_kyc_pending: int

    @classmethod
    def generate_mock(cls) -> PartnerBizKpiSummaryDomainModel:
        return cls(
            total_property_partners=mockutils.random.randint(100, 500),
            number_active=mockutils.random.randint(50, 100),
            number_pending_approval=mockutils.random.randint(10, 50),
            number_rejected=mockutils.random.randint(5, 20),
            number_suspended=mockutils.random.randint(5, 20),
            number_kyc_pending=mockutils.random.randint(10, 30),
        )


@dataclass
class PropertyPartnerDomainModel:
    property_partner_id: str
    property_partner_email: str
    property_name: str
    property_location: str
    property_type: str  # TODO: list of property types
    property_source: PropertySourceEnum
    property_status: PropertyStatusEnum
    partner_kyc_status: PartnerKYCStatusEnum
    property_room_count: int
    last_updated: datetime

    @classmethod
    def generate_mock(cls) -> PropertyPartnerDomainModel:
        return cls(
            property_partner_id=mockutils.random_user_id(),
            property_partner_email=mockutils.random_user_email(),
            property_name=mockutils.random_property_name(),
            property_location=mockutils.random_property_location(),
            property_type=mockutils.random_property_type(),
            property_source=mockutils.random.choice(list(PropertySourceEnum)),
            property_status=mockutils.random.choice(list(PropertyStatusEnum)),
            partner_kyc_status=mockutils.random.choice(list(PartnerKYCStatusEnum)),
            property_room_count=mockutils.random.randint(1, 10),
            last_updated=mockutils.random_date_from_past_days(),
        )
