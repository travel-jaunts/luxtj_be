from datetime import date

from luxtj.contexts.customer.application.bucket_list_recommendation_engine.models import (
    HotelDeal,
    HotelTier,
)
from luxtj.contexts.customer.application.bucket_list_recommendation_engine.providers.interfaces import (
    HotelInventoryProvider,
)
from luxtj.contexts.customer.domain.errors import (
    BucketListRecommendationProviderNotConfiguredError,
)


class PendingHotelInventoryProvider(HotelInventoryProvider):
    """Placeholder until the backend's hotel inventory source is connected."""

    def get_hotel_deals(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        tier: HotelTier,
    ) -> list[HotelDeal]:
        raise BucketListRecommendationProviderNotConfiguredError(
            "Hotel inventory provider is not configured for bucket-list recommendations"
        )
