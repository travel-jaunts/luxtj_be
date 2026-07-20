from datetime import date

from luxtj.contexts.customer.application.bucket_list_recommendation_engine.models import FlightDeal
from luxtj.contexts.customer.application.bucket_list_recommendation_engine.providers.interfaces import (
    FlightInventoryProvider,
)
from luxtj.contexts.customer.domain.errors import (
    BucketListRecommendationProviderNotConfiguredError,
)


class PendingFlightInventoryProvider(FlightInventoryProvider):
    """Placeholder until the backend's flight inventory source is connected."""

    def get_flight_deals(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        is_outbound: bool,
        is_return: bool,
    ) -> list[FlightDeal]:
        raise BucketListRecommendationProviderNotConfiguredError(
            "Flight inventory provider is not configured for bucket-list recommendations"
        )
