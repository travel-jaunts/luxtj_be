from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CustomerTierEnum(StrEnum):
    """Enum to represent different user tiers (e.g., Standard, World Wise)
    - more tiers to be added
    """

    NOVUS = "Novus"
    AUREA = "Aurea"
    PRIVE = "Privé"
    ELITE = "Elite"
    ECHELON = "Échelon"


@dataclass
class CustomerBizKpiSummaryDomainModel:
    amount_currency: str
    total_revenue: float
    average_order_value: float
    total_customers: int
    active_customers: int
    repeat_rate: float
    cancellation_rate: float
    customers_by_tier: dict[CustomerTierEnum, int]


@dataclass
class CustomerDomainModel:
    user_id: str
    user_amount_currency: str
    user_first_name: str
    user_last_name: str
    user_email: str
    user_phone_number: str
    user_base_location: str
    user_registration_date: datetime  # ISO format date string
    user_last_booking_date: datetime | None  # ISO format date string, can be null
    user_total_spend: float
    user_booking_count: int
    user_average_order_value: float
    user_cancellation_count: int
    user_is_active: bool
    user_tier: CustomerTierEnum  # e.g., "Novus", "Aurea"
    user_status: str  # e.g., "Active", "Inactive"

    @property
    def user_cancellation_rate(self) -> float:
        if self.user_booking_count == 0:
            return 0.0
        return (self.user_cancellation_count / self.user_booking_count) * 100
