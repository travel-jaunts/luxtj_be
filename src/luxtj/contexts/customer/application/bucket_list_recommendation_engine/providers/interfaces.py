"""Abstract interfaces for external flight and hotel inventory providers."""

from abc import ABC, abstractmethod
from datetime import date

from ..models import FlightDeal, HotelDeal, HotelTier


class FlightInventoryProvider(ABC):
    """Abstract interface for querying normalized flight inventory."""

    @abstractmethod
    def get_flight_deals(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        is_outbound: bool,
        is_return: bool,
    ) -> list[FlightDeal]:
        """Return normalized flight deals for one route and departure date."""
        pass


class HotelInventoryProvider(ABC):
    """Abstract interface for querying normalized hotel inventory."""

    @abstractmethod
    def get_hotel_deals(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        tier: HotelTier,
    ) -> list[HotelDeal]:
        """Return normalized hotel deals for one stay and requested tier."""
        pass
