from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from luxtj.contexts.action_centre.domain.item import ActionItem


class ActionItemRepository(Protocol):
    async def upsert_pending(
        self,
        *,
        workflow: str,
        entity_id: str,
        occurred_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        """Create a pending item, or no-op if a row for (workflow, entity_id) already exists."""

    async def mark_resolved(
        self,
        *,
        workflow: str,
        entity_id: str,
        occurred_at: datetime,
    ) -> None:
        """Flip a (workflow, entity_id) row to resolved. If absent, insert as resolved (out-of-order safe)."""

    async def count_pending_by_workflow(self) -> dict[str, int]:
        """Return {workflow_key -> pending_count}."""

    async def oldest_pending_at_by_workflow(self) -> dict[str, datetime]:
        """Return {workflow_key -> oldest pending created_at} for workflows with pending items."""

    async def list_for_workflow(
        self,
        workflow: str,
        *,
        status: str | None = None,
    ) -> list[ActionItem]:
        """Used in tests / debugging."""


class ProcessedOutboxCursor(Protocol):
    async def get_last_processed_id(self) -> str | None: ...

    async def set_last_processed_id(self, outbox_id: str) -> None: ...


class OutboxEventReader(Protocol):
    async def fetch_after(
        self,
        *,
        cursor_id: str | None,
        types: list[str],
        limit: int,
    ) -> list[OutboxRecord]:
        """Return outbox rows of given types with id > cursor_id, ordered by id ascending."""


class OutboxRecord(Protocol):
    id: str
    type: str
    subject: str | None
    time: datetime | None
    payload: dict[str, Any]
