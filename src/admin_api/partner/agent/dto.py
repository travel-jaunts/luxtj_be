from dataclasses import dataclass


@dataclass
class UpdateAgentPartnerDetailsDTO:
    company_name: str
    contact: str
    email: str
    city: str
    website: str
    commission_percent: float
    domestic_percent: float
    international_percent: float
