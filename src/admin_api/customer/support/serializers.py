from pydantic import AwareDatetime

from admin_api.customer.support.domainmodel import SupportKpiSummary, SupportTicketDomainModel
from admin_api.customer.users.domainmodel import CustomerDomainModel
from common.serializerlib import (
    ApiSerializerBaseModel,
)
from luxtj.domain.enums import (
    CustomerTierEnum,
    SupportCategoryEnum,
    SupportTicketPriorityEnum,
    SupportTicketStatusEnum,
)


class SupportKpiSummarySerializer(ApiSerializerBaseModel):
    total_tickets: int
    open_tickets: int
    average_resolution_time_hours: float
    escalation_rate_percent: float

    @classmethod
    def from_domain_model(
        cls, support_kpi_summary: SupportKpiSummary
    ) -> SupportKpiSummarySerializer:
        return cls(
            total_tickets=support_kpi_summary.total_tickets,
            open_tickets=support_kpi_summary.open_tickets,
            average_resolution_time_hours=support_kpi_summary.average_resolution_time_hours,
            escalation_rate_percent=support_kpi_summary.escalation_rate_percent,
        )


class AgentDetailModel(ApiSerializerBaseModel):
    agent_id: str
    agent_first_name: str
    agent_last_name: str
    agent_email: str
    agent_phone_number: str

    @classmethod
    def from_domain_model(cls, agent_model: CustomerDomainModel) -> AgentDetailModel:
        return cls(
            agent_id=agent_model.user_id,
            agent_first_name=agent_model.user_first_name,
            agent_last_name=agent_model.user_last_name,
            agent_email=agent_model.user_email,
            agent_phone_number=agent_model.user_phone_number,
        )


class SupportCustomer(ApiSerializerBaseModel):
    user_id: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_tier: CustomerTierEnum
    user_phone_number: str

    @classmethod
    def from_domain_model(cls, customer_model: CustomerDomainModel) -> SupportCustomer:
        return cls(
            user_id=customer_model.user_id,
            user_first_name=customer_model.user_first_name,
            user_last_name=customer_model.user_last_name,
            user_email=customer_model.user_email,
            user_tier=customer_model.user_tier,
            user_phone_number=customer_model.user_phone_number,
        )


class SupportTicketLineItem(ApiSerializerBaseModel):
    ticket_id: str
    customer: SupportCustomer
    booking_id: str | None
    category: SupportCategoryEnum
    status: SupportTicketStatusEnum
    priority: SupportTicketPriorityEnum
    created_date: AwareDatetime
    resolution_date: AwareDatetime | None
    subject: str
    description: str
    assigned_agent: AgentDetailModel | None

    @classmethod
    def from_domain_model(cls, ticket_model: SupportTicketDomainModel) -> SupportTicketLineItem:
        return cls(
            ticket_id=ticket_model.ticket_id,
            customer=SupportCustomer.from_domain_model(ticket_model.customer),
            booking_id=ticket_model.booking_id,
            category=ticket_model.category,
            status=ticket_model.status,
            priority=ticket_model.priority,
            created_date=ticket_model.created_date,
            resolution_date=ticket_model.resolution_date,
            subject=ticket_model.subject,
            description=ticket_model.description,
            assigned_agent=AgentDetailModel.from_domain_model(ticket_model.assigned_agent)
            if ticket_model.assigned_agent
            else None,
        )
