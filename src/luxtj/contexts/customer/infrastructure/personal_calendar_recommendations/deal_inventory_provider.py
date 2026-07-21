from collections.abc import Sequence

from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.models import (
    DealCandidate,
    DealSearchRequest,
)


class PendingPersonalCalendarDealInventoryProvider:
    async def search_deals(self, request: DealSearchRequest) -> Sequence[DealCandidate]:
        raise RuntimeError(
            "Personal-calendar deal inventory provider is not configured; "
            f"cannot search {request.plan_type.value} {request.tier.value} inventory"
        )
