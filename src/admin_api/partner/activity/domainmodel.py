from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from luxtj.domain.enums import PartnerKYCStatusEnum
from luxtj.utils import mockutils


class ActivityPartnerStatusEnum(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class ActivityBankDetailsDomainModel:
    account_holder_name: str
    account_number: str
    ifsc_code: str
    bank_name: str

    @classmethod
    def generate_mock(cls) -> ActivityBankDetailsDomainModel:
        return cls(
            account_holder_name=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            account_number=str(mockutils.random.randint(100000000000, 999999999999)),
            ifsc_code="MOCK0001234",
            bank_name="Mock Bank",
        )


@dataclass
class ActivityDocumentDomainModel:
    luxtj_id: str
    url: str
    image_size_bytes: int
    mime_type: str
    alt_text: str | None

    @classmethod
    def generate_mock(cls, *, alt_text: str) -> ActivityDocumentDomainModel:
        return cls(
            luxtj_id=mockutils.random_booking_id(),
            url="https://example.com/mock-document.pdf",
            image_size_bytes=mockutils.random.randint(50000, 500000),
            mime_type="application/pdf",
            alt_text=alt_text,
        )


@dataclass
class ActivityPriceDomainModel:
    amount: float
    currency: str

    @classmethod
    def generate_mock(cls) -> ActivityPriceDomainModel:
        return cls(
            amount=mockutils.random_booking_amount(500, 25000),
            currency="INR",
        )


@dataclass
class ActivityPartnerDetailsDomainModel:
    partner_id: str
    company_name: str
    contact_person: str
    phone: str
    email: str
    activities: list[str]
    per_person_price: ActivityPriceDomainModel
    group_price: ActivityPriceDomainModel
    seasonal_price: ActivityPriceDomainModel
    open_months_weeks_days: str
    timings: str
    capacity: int
    license_document: ActivityDocumentDomainModel
    insurance_document: ActivityDocumentDomainModel
    bank_details: ActivityBankDetailsDomainModel

    @classmethod
    def generate_mock(cls) -> ActivityPartnerDetailsDomainModel:
        return cls(
            partner_id=mockutils.random_user_id(),
            company_name=f"{mockutils.random_user_last_name()} Adventures",
            contact_person=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            phone=mockutils.random_user_phone_number(),
            email=mockutils.random_user_email(),
            activities=[
                "Skiing",
                "Trekking",
                "ATV Ride",
                "Shikara Ride",
                "Safari",
                "Local Tours",
            ],
            per_person_price=ActivityPriceDomainModel.generate_mock(),
            group_price=ActivityPriceDomainModel.generate_mock(),
            seasonal_price=ActivityPriceDomainModel.generate_mock(),
            open_months_weeks_days="All months / Mon-Sat",
            timings="09:00 - 18:00",
            capacity=mockutils.random.randint(10, 80),
            license_document=ActivityDocumentDomainModel.generate_mock(alt_text="Activity License"),
            insurance_document=ActivityDocumentDomainModel.generate_mock(
                alt_text="Activity Insurance"
            ),
            bank_details=ActivityBankDetailsDomainModel.generate_mock(),
        )


@dataclass
class ActivityPartnerBizKpiSummaryDomainModel:
    total_activity_partners: int
    number_active: int
    number_pending: int
    number_suspended: int
    number_kyc_pending: int

    @classmethod
    def generate_mock(cls) -> ActivityPartnerBizKpiSummaryDomainModel:
        return cls(
            total_activity_partners=mockutils.random.randint(80, 300),
            number_active=mockutils.random.randint(40, 180),
            number_pending=mockutils.random.randint(10, 70),
            number_suspended=mockutils.random.randint(5, 30),
            number_kyc_pending=mockutils.random.randint(10, 60),
        )


@dataclass
class ActivityPartnerDomainModel:
    partner_id: str
    activity_name: str
    partner_name: str
    location: str
    activity_type: str
    status: ActivityPartnerStatusEnum
    kyc_status: PartnerKYCStatusEnum
    last_updated: datetime

    @classmethod
    def generate_mock(cls) -> ActivityPartnerDomainModel:
        return cls(
            partner_id=mockutils.random_user_id(),
            activity_name=mockutils.random.choice(
                [
                    "Skiing",
                    "Trekking",
                    "ATV Ride",
                    "Shikara Ride",
                    "Safari",
                    "Local Tours",
                ]
            ),
            partner_name=f"{mockutils.random_user_last_name()} Adventures",
            location=mockutils.random_property_location(),
            activity_type=mockutils.random.choice(
                ["Adventure", "Water", "Wildlife", "Sightseeing"]
            ),
            status=mockutils.random.choice(list(ActivityPartnerStatusEnum)),
            kyc_status=mockutils.random.choice(list(PartnerKYCStatusEnum)),
            last_updated=mockutils.random_date_from_past_days(),
        )
