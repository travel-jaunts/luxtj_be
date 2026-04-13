from dataclasses import dataclass


@dataclass
class UpdateActivityPartnerDetailsDTO:
    company_name: str
    contact_person: str
    phone: str
    email: str
    activities: list[str]
    per_person_price_amount: float
    per_person_price_currency: str
    group_price_amount: float
    group_price_currency: str
    seasonal_price_amount: float
    seasonal_price_currency: str
    open_months_weeks_days: str
    timings: str
    capacity: int
