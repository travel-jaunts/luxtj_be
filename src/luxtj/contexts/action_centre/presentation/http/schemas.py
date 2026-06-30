from datetime import datetime
from typing import Any

from pydantic import Field

from luxtj.contexts.action_centre.application.queries import Summary, SummaryCard
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class SummaryCardSerializer(ApiSerializerBaseModel):
    workflow: str = Field(..., description="Workflow key used by the frontend to resolve a route.")
    label: str = Field(..., description="Human-readable card label.")
    count: int = Field(..., description="Number of pending items for this workflow.")
    oldest_pending_at: datetime | None = Field(
        None, description="Timestamp of the oldest pending item; null when count is 0."
    )
    filter: dict[str, Any] = Field(
        ..., description="Filter the frontend should apply when deep-linking to the workflow page."
    )

    @classmethod
    def from_card(cls, card: SummaryCard) -> SummaryCardSerializer:
        return cls(
            workflow=card.workflow,
            label=card.label,
            count=card.count,
            oldest_pending_at=card.oldest_pending_at,
            filter=dict(card.filter),
        )


class SummarySerializer(ApiSerializerBaseModel):
    cards: list[SummaryCardSerializer]
    generated_at: datetime

    @classmethod
    def from_summary(cls, summary: Summary) -> SummarySerializer:
        return cls(
            cards=[SummaryCardSerializer.from_card(card) for card in summary.cards],
            generated_at=summary.generated_at,
        )
