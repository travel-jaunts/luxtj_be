from datetime import datetime
from typing import Any

from luxtj.contexts.action_centre.domain.enums import ActionItemStatus
from luxtj.contexts.action_centre.domain.item import ActionItem


class InMemoryActionItemRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], ActionItem] = {}

    async def upsert_pending(
        self,
        *,
        workflow: str,
        entity_id: str,
        occurred_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        key = (workflow, entity_id)
        existing = self._items.get(key)
        if existing is None:
            self._items[key] = ActionItem(
                workflow=workflow,
                entity_id=entity_id,
                status=ActionItemStatus.PENDING,
                created_at=occurred_at,
                metadata=dict(metadata),
                resolved_at=None,
            )
            return
        if existing.status == ActionItemStatus.RESOLVED and (
            existing.resolved_at is None or occurred_at > existing.resolved_at
        ):
            existing.status = ActionItemStatus.PENDING
            existing.resolved_at = None
            existing.created_at = occurred_at
            existing.metadata = dict(metadata)

    async def mark_resolved(
        self,
        *,
        workflow: str,
        entity_id: str,
        occurred_at: datetime,
    ) -> None:
        key = (workflow, entity_id)
        existing = self._items.get(key)
        if existing is None:
            self._items[key] = ActionItem(
                workflow=workflow,
                entity_id=entity_id,
                status=ActionItemStatus.RESOLVED,
                created_at=occurred_at,
                metadata={},
                resolved_at=occurred_at,
            )
            return
        if existing.status == ActionItemStatus.RESOLVED:
            return
        existing.resolve(occurred_at)

    async def count_pending_by_workflow(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self._items.values():
            if item.status == ActionItemStatus.PENDING:
                counts[item.workflow] = counts.get(item.workflow, 0) + 1
        return counts

    async def oldest_pending_at_by_workflow(self) -> dict[str, datetime]:
        oldest: dict[str, datetime] = {}
        for item in self._items.values():
            if item.status != ActionItemStatus.PENDING:
                continue
            current = oldest.get(item.workflow)
            if current is None or item.created_at < current:
                oldest[item.workflow] = item.created_at
        return oldest

    async def list_for_workflow(
        self,
        workflow: str,
        *,
        status: str | None = None,
    ) -> list[ActionItem]:
        items = [item for item in self._items.values() if item.workflow == workflow]
        if status is not None:
            items = [item for item in items if item.status.value == status]
        return sorted(items, key=lambda i: i.created_at)
