from dataclasses import dataclass
from datetime import datetime

from admin_api.customer.users.domainmodel import CustomerDomainModel

from luxtj.utils import mockutils
from luxtj.domain.enums import (
    SupportCategoryEnum,
    SupportTicketStatusEnum,
    SupportTicketPriorityEnum,
)


@dataclass
class SupportKpiSummary:
    total_tickets: int
    open_tickets: int
    average_resolution_time_hours: float
    escalation_rate_percent: float

    @classmethod
    def generate_mock(cls) -> "SupportKpiSummary":
        return cls(
            total_tickets=mockutils.random.randint(10, 20),
            open_tickets=mockutils.random.randint(1, 10),
            average_resolution_time_hours=mockutils.random.uniform(1.0, 48.0),
            escalation_rate_percent=mockutils.random.uniform(0.0, 100.0),
        )


@dataclass
class SupportTicketDomainModel:
    ticket_id: str
    customer: CustomerDomainModel
    booking_id: str
    category: SupportCategoryEnum
    status: SupportTicketStatusEnum
    priority: SupportTicketPriorityEnum
    created_date: datetime
    resolution_date: datetime | None
    subject: str
    description: str
    assigned_agent: CustomerDomainModel | None

    @classmethod
    def generate_mock(cls) -> "SupportTicketDomainModel":
        return cls(
            ticket_id=mockutils.random_booking_id(),
            customer=CustomerDomainModel.generate_mock(mock_currency="INR"),
            booking_id=mockutils.random_booking_id(),
            category=mockutils.random.choice(list(SupportCategoryEnum)),
            status=mockutils.random.choice(list(SupportTicketStatusEnum)),
            priority=mockutils.random.choice(list(SupportTicketPriorityEnum)),
            created_date=mockutils.random_registration_date(),
            resolution_date=None,
            subject=mockutils.random_support_ticket_subject(),
            description=mockutils.random_support_ticket_description(),
            assigned_agent=CustomerDomainModel.generate_mock(mock_currency="INR"),
        )
