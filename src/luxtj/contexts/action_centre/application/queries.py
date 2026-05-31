from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SummaryCard:
    workflow: str
    label: str
    count: int
    oldest_pending_at: datetime | None
    filter: dict[str, Any]


@dataclass(frozen=True)
class Summary:
    cards: list[SummaryCard]
    generated_at: datetime
