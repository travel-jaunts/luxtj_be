from dataclasses import dataclass
from datetime import datetime

from luxtj.domain.enums import PartnerKYCStatusEnum, PropertySourceEnum, PropertyStatusEnum
from luxtj.utils import mockutils


@dataclass
class PropertyImageDomainModel:
    luxtj_id: str
    url: str
    image_size_bytes: int
    mime_type: str
    alt_text: str | None

    @classmethod
    def generate_mock(cls) -> PropertyImageDomainModel:
        return cls(
            luxtj_id=mockutils.random_booking_id(),
            url="https://example.com/mock-image.jpg",
            image_size_bytes=mockutils.random.randint(50000, 500000),
            mime_type="image/jpeg",
            alt_text="Mock Property Image",
        )


@dataclass
class PropertyBankDetailsDomainModel:
    account_holder_name: str
    account_number: str
    ifsc_code: str
    bank_name: str

    @classmethod
    def generate_mock(cls) -> PropertyBankDetailsDomainModel:
        return cls(
            account_holder_name=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            account_number=str(mockutils.random.randint(100000000000, 999999999999)),
            ifsc_code="MOCK0001234",
            bank_name="Mock Bank",
        )


@dataclass
class PropertyLocationDomainModel:
    latitude: float
    longitude: float
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    postal_code: str
    country: str

    @classmethod
    def generate_mock(cls) -> PropertyLocationDomainModel:
        return cls(
            latitude=round(mockutils.random.uniform(-90, 90), 4),
            longitude=round(mockutils.random.uniform(-180, 180), 4),
            address_line1="123 Mock Street",
            address_line2=None,
            city=mockutils.random_property_location(),
            state="Mock State",
            postal_code="123456",
            country="India",
        )


@dataclass
class PropertyPartnerDetailsDomainModel:
    partner_id: str
    property_name: str
    property_owner_name: str
    property_contact_number: str
    partner_email: str
    property_address: str
    property_images: list[PropertyImageDomainModel]
    property_room_types: list[str]
    property_amenities: list[str]
    property_description: str
    property_location: PropertyLocationDomainModel
    property_base_price_amount: float
    property_base_price_currency: str
    seasonal_price_amount: float
    seasonal_price_currency: str
    partner_pan_number: str
    partner_gst_number: str
    partner_bank: PropertyBankDetailsDomainModel
    kyc_documents: list[PropertyImageDomainModel]

    @classmethod
    def generate_mock(cls) -> PropertyPartnerDetailsDomainModel:
        return cls(
            partner_id=mockutils.random_user_id(),
            property_name=mockutils.random_property_name(),
            property_owner_name=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            property_contact_number=mockutils.random_user_phone_number(),
            partner_email=mockutils.random_user_email(),
            property_address="123 Mock Street, Mock City, India",
            property_images=[PropertyImageDomainModel.generate_mock() for _ in range(3)],
            property_room_types=mockutils.random.choices(
                ["Deluxe", "Suite", "Standard", "Executive"],
                k=mockutils.random.randint(1, 3),
            ),
            property_amenities=mockutils.random.choices(
                ["Free Wi-Fi", "Swimming Pool", "Gym", "Spa", "Parking", "Restaurant"],
                k=mockutils.random.randint(2, 5),
            ),
            property_description="This is a mock property description for a luxury hotel.",
            property_location=PropertyLocationDomainModel.generate_mock(),
            property_base_price_amount=mockutils.random_booking_amount(1000, 50000),
            property_base_price_currency="INR",
            seasonal_price_amount=mockutils.random_booking_amount(2000, 80000),
            seasonal_price_currency="INR",
            partner_pan_number="ABCDE1234F",
            partner_gst_number="22ABCDE1234F1Z5",
            partner_bank=PropertyBankDetailsDomainModel.generate_mock(),
            kyc_documents=[PropertyImageDomainModel.generate_mock()],
        )


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
