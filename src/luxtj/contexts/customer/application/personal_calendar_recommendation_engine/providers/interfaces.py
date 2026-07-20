from collections.abc import Sequence
from typing import Protocol

from ..models import DealCandidate, DealSearchRequest


class DealInventoryProvider(Protocol):
    """Backend infrastructure boundary returning normalized candidates only."""

    async def search_deals(self, request: DealSearchRequest) -> Sequence[DealCandidate]: ...
