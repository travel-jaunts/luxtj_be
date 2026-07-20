from typing import Protocol

from ..models import RankingObservation


class RankingObserver(Protocol):
    """Optional backend boundary for recording ranking impressions and ML feedback data."""

    async def record_ranking(self, observation: RankingObservation) -> None: ...
