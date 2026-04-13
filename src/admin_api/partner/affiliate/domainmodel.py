from dataclasses import dataclass
from enum import StrEnum

from luxtj.utils import mockutils


class AffiliatePartnerStatusEnum(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class AffiliatePartnerBizKpiSummaryDomainModel:
    total_affiliates: int
    number_active: int
    number_pending: int
    earnings_amount: float
    earnings_currency: str

    @classmethod
    def generate_mock(
        cls, *, iso_currency_str: str = "INR"
    ) -> AffiliatePartnerBizKpiSummaryDomainModel:
        total_affiliates = mockutils.random.randint(100, 500)
        number_active = mockutils.random.randint(40, total_affiliates)
        number_pending = mockutils.random.randint(5, max(5, total_affiliates - number_active))
        earnings_amount = mockutils.random_booking_amount(100000, 15000000)
        return cls(
            total_affiliates=total_affiliates,
            number_active=number_active,
            number_pending=number_pending,
            earnings_amount=earnings_amount,
            earnings_currency=iso_currency_str,
        )


@dataclass
class AffiliatePartnerDomainModel:
    partner_id: str
    affiliate_name: str
    platform: str
    traffic: int
    commission_percent: float
    earnings_amount: float
    earnings_currency: str
    status: AffiliatePartnerStatusEnum

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str = "INR") -> AffiliatePartnerDomainModel:
        affiliate_name = f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}"
        platform = mockutils.random.choice(
            ["instagram", "youtube", "website", "blog", "newsletter"]
        )
        return cls(
            partner_id=mockutils.random_user_id(),
            affiliate_name=affiliate_name,
            platform=platform,
            traffic=mockutils.random.randint(1000, 250000),
            commission_percent=round(mockutils.random.uniform(1.0, 20.0), 2),
            earnings_amount=mockutils.random_booking_amount(1000, 3000000),
            earnings_currency=iso_currency_str,
            status=mockutils.random.choice(list(AffiliatePartnerStatusEnum)),
        )


@dataclass
class AffiliatePartnerDetailsDomainModel:
    partner_id: str

    name: str
    website: str
    social_media: str
    contact: str

    affiliate_link: str
    clicks: int
    bookings: int
    revenue_amount: float
    revenue_currency: str
    commission_percent: float

    payments_paid_amount: float
    payments_pending_amount: float
    payments_currency: str

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str = "INR") -> AffiliatePartnerDetailsDomainModel:
        name = f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}"
        handle = f"{name.lower().replace(' ', '')}_{mockutils.random.randint(10, 99)}"
        return cls(
            partner_id=mockutils.random_user_id(),
            name=name,
            website=f"https://{handle}.example.com",
            social_media=f"@{handle}",
            contact=mockutils.random_user_phone_number(),
            affiliate_link=f"https://luxtj.example.com/r/{mockutils.random_user_id()[:8]}",
            clicks=mockutils.random.randint(100, 500000),
            bookings=mockutils.random.randint(0, 5000),
            revenue_amount=mockutils.random_booking_amount(5000, 25000000),
            revenue_currency=iso_currency_str,
            commission_percent=round(mockutils.random.uniform(1.0, 20.0), 2),
            payments_paid_amount=mockutils.random_booking_amount(0, 10000000),
            payments_pending_amount=mockutils.random_booking_amount(0, 3000000),
            payments_currency=iso_currency_str,
        )
