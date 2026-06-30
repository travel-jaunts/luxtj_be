from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from luxtj.contexts.action_centre.domain.enums import ActionItemStatus


@dataclass
class ActionItem:
    workflow: str
    entity_id: str
    status: ActionItemStatus
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    resolved_at: datetime | None = None

    @property
    def natural_key(self) -> tuple[str, str]:
        return (self.workflow, self.entity_id)

    def resolve(self, when: datetime) -> None:
        self.status = ActionItemStatus.RESOLVED
        self.resolved_at = when
