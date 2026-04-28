from pydantic import AwareDatetime

from admin_api.partner.agent.domainmodel import (
    AgentPartnerBizKpiSummaryDomainModel,
    AgentPartnerDetailsDomainModel,
    AgentPartnerDomainModel,
    AgentPartnerStatusEnum,
)
from admin_api.partner.agent.dto import UpdateAgentPartnerDetailsDTO
from common.serializerlib import (
    AmountSerializer,
    ApiSerializerBaseModel,
    BankDetailsSerializer,
)


class AgentPartnerBizKpiSummary(ApiSerializerBaseModel):
    total_agents: int
    number_active: int
    number_pending: int
    commission_assigned: AmountSerializer

    @classmethod
    def from_domain_model(
        cls, domain_model: AgentPartnerBizKpiSummaryDomainModel
    ) -> AgentPartnerBizKpiSummary:
        return cls(
            total_agents=domain_model.total_agents,
            number_active=domain_model.number_active,
            number_pending=domain_model.number_pending,
            commission_assigned=AmountSerializer(
                amount=domain_model.commission_assigned_amount,
                currency=domain_model.commission_currency,
            ),
        )


class AgentPartnerLineItem(ApiSerializerBaseModel):
    partner_id: str
    agent_name: str
    company: str
    city: str
    commission_percent: float
    status: AgentPartnerStatusEnum
    sales: AmountSerializer
    last_login: AwareDatetime

    @classmethod
    def from_domain_model(cls, domain_model: AgentPartnerDomainModel) -> AgentPartnerLineItem:
        return cls(
            partner_id=domain_model.partner_id,
            agent_name=domain_model.agent_name,
            company=domain_model.company,
            city=domain_model.city,
            commission_percent=domain_model.commission_percent,
            status=domain_model.status,
            sales=AmountSerializer(
                amount=domain_model.sales_amount,
                currency=domain_model.sales_currency,
            ),
            last_login=domain_model.last_login,
        )


class AgentPartnerDetails(ApiSerializerBaseModel):
    partner_id: str

    company_name: str
    contact: str
    email: str
    city: str
    website: str
    commission_percent: float

    domestic_percent: float
    international_percent: float
    custom_deals: int

    bookings: int
    revenue: AmountSerializer
    active_leads: int

    gst: str
    pan: str
    bank: BankDetailsSerializer

    @classmethod
    def from_domain_model(cls, domain_model: AgentPartnerDetailsDomainModel) -> AgentPartnerDetails:
        return cls(
            partner_id=domain_model.partner_id,
            company_name=domain_model.company_name,
            contact=domain_model.contact,
            email=domain_model.email,
            city=domain_model.city,
            website=domain_model.website,
            commission_percent=domain_model.commission_percent,
            domestic_percent=domain_model.domestic_percent,
            international_percent=domain_model.international_percent,
            custom_deals=domain_model.custom_deals,
            bookings=domain_model.bookings,
            revenue=AmountSerializer(
                amount=domain_model.revenue_amount,
                currency=domain_model.revenue_currency,
            ),
            active_leads=domain_model.active_leads,
            gst=domain_model.gst,
            pan=domain_model.pan,
            bank=BankDetailsSerializer(
                account_holder_name=domain_model.bank.account_holder_name,
                account_number=domain_model.bank.account_number,
                ifsc_code=domain_model.bank.ifsc_code,
                bank_name=domain_model.bank.bank_name,
            ),
        )


class UpdateAgentPartnerDetailsBody(ApiSerializerBaseModel):
    company_name: str
    contact: str
    email: str
    city: str
    website: str

    commission_percent: float
    domestic_percent: float
    international_percent: float

    def to_dto(self) -> UpdateAgentPartnerDetailsDTO:
        return UpdateAgentPartnerDetailsDTO(
            company_name=self.company_name,
            contact=self.contact,
            email=self.email,
            city=self.city,
            website=self.website,
            commission_percent=self.commission_percent,
            domestic_percent=self.domestic_percent,
            international_percent=self.international_percent,
        )
