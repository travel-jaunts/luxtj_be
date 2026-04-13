from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from luxtj.utils import mockutils


class AgentPartnerStatusEnum(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class AgentPartnerBizKpiSummaryDomainModel:
    total_agents: int
    number_active: int
    number_pending: int
    commission_assigned_amount: float
    commission_currency: str

    @classmethod
    def generate_mock(
        cls, *, iso_currency_str: str = "INR"
    ) -> AgentPartnerBizKpiSummaryDomainModel:
        total_agents = mockutils.random.randint(100, 500)
        number_active = mockutils.random.randint(40, total_agents)
        number_pending = mockutils.random.randint(5, max(5, total_agents - number_active))
        commission_assigned_amount = mockutils.random.randint(0, total_agents)
        return cls(
            total_agents=total_agents,
            number_active=number_active,
            number_pending=number_pending,
            commission_assigned_amount=commission_assigned_amount,
            commission_currency=iso_currency_str,
        )


@dataclass
class AgentPartnerDomainModel:
    partner_id: str
    agent_name: str
    company: str
    city: str
    commission_percent: float
    status: AgentPartnerStatusEnum
    sales_amount: float
    sales_currency: str
    last_login: datetime

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str = "INR") -> AgentPartnerDomainModel:
        agent_name = f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}"
        return cls(
            partner_id=mockutils.random_user_id(),
            agent_name=agent_name,
            company=f"{mockutils.random_user_last_name()} Travels",
            city=mockutils.random_property_location(),
            commission_percent=round(mockutils.random.uniform(2.0, 18.0), 2),
            status=mockutils.random.choice(list(AgentPartnerStatusEnum)),
            sales_amount=mockutils.random_booking_amount(10000, 500000),
            sales_currency=iso_currency_str,
            last_login=mockutils.random_date_from_past_days(),
        )


@dataclass
class AgentPartnerBankDetailsDomainModel:
    account_holder_name: str
    account_number: str
    ifsc_code: str
    bank_name: str

    @classmethod
    def generate_mock(cls) -> AgentPartnerBankDetailsDomainModel:
        return cls(
            account_holder_name=f"{mockutils.random_user_first_name()} {mockutils.random_user_last_name()}",
            account_number=str(mockutils.random.randint(100000000000, 999999999999)),
            ifsc_code="MOCK0001234",
            bank_name="Mock Bank",
        )


@dataclass
class AgentPartnerDetailsDomainModel:
    partner_id: str

    company_name: str
    contact: str
    email: str
    city: str
    website: str
    commission_percent: float

    domestic_percent: float
    international_percent: float
    custom_deals: bool
    sales_performance: float

    bookings: int
    revenue_amount: float
    revenue_currency: str
    active_leads: int

    gst: str
    pan: str
    bank: AgentPartnerBankDetailsDomainModel

    @classmethod
    def generate_mock(cls, *, iso_currency_str: str = "INR") -> AgentPartnerDetailsDomainModel:
        company_name = f"{mockutils.random_user_last_name()} Travel Co"
        return cls(
            partner_id=mockutils.random_user_id(),
            company_name=company_name,
            contact=mockutils.random_user_phone_number(),
            email=mockutils.random_user_email(),
            city=mockutils.random_property_location(),
            website=f"https://{company_name.lower().replace(' ', '')}.example.com",
            commission_percent=round(mockutils.random.uniform(2.0, 18.0), 2),
            domestic_percent=round(mockutils.random.uniform(10.0, 90.0), 2),
            international_percent=round(mockutils.random.uniform(10.0, 90.0), 2),
            custom_deals=mockutils.random.choice([True, False]),
            sales_performance=round(mockutils.random.uniform(0.0, 100.0), 2),
            bookings=mockutils.random.randint(10, 2000),
            revenue_amount=mockutils.random_booking_amount(50000, 5000000),
            revenue_currency=iso_currency_str,
            active_leads=mockutils.random.randint(0, 500),
            gst="22ABCDE1234F1Z5",
            pan="ABCDE1234F",
            bank=AgentPartnerBankDetailsDomainModel.generate_mock(),
        )
