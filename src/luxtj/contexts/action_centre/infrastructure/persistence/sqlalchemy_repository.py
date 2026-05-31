from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.action_centre.domain.enums import ActionItemStatus
from luxtj.contexts.action_centre.domain.item import ActionItem
from luxtj.contexts.action_centre.infrastructure.persistence.sqlalchemy_models import (
    ActionCentreItemRow,
    ActionCentreOutboxCursorRow,
)
from luxtj.shared_kernel.infrastructure.persistence.outbox_model import DomainEventOutboxRow
from luxtj.utils import timeutils


class SqlAlchemyActionItemRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert_pending(
        self,
        *,
        workflow: str,
        entity_id: str,
        occurred_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        row = await self._get(workflow, entity_id)
        if row is None:
            self._session.add(
                ActionCentreItemRow(
                    workflow=workflow,
                    entity_id=entity_id,
                    status=ActionItemStatus.PENDING.value,
                    item_metadata=metadata,
                    created_at=occurred_at,
                    resolved_at=None,
                )
            )
            return
        # Already exists. If currently resolved with an earlier occurred_at, treat as out-of-order
        # and ignore. Otherwise leave the existing pending row alone (idempotent).
        if row.status == ActionItemStatus.RESOLVED.value and (
            row.resolved_at is None or occurred_at > row.resolved_at
        ):
            row.status = ActionItemStatus.PENDING.value
            row.resolved_at = None
            row.created_at = occurred_at
            row.item_metadata = metadata

    async def mark_resolved(
        self,
        *,
        workflow: str,
        entity_id: str,
        occurred_at: datetime,
    ) -> None:
        row = await self._get(workflow, entity_id)
        if row is None:
            self._session.add(
                ActionCentreItemRow(
                    workflow=workflow,
                    entity_id=entity_id,
                    status=ActionItemStatus.RESOLVED.value,
                    item_metadata={},
                    created_at=occurred_at,
                    resolved_at=occurred_at,
                )
            )
            return
        if row.status == ActionItemStatus.RESOLVED.value:
            return  # idempotent
        row.status = ActionItemStatus.RESOLVED.value
        row.resolved_at = occurred_at

    async def count_pending_by_workflow(self) -> dict[str, int]:
        result = await self._session.execute(
            select(ActionCentreItemRow.workflow, func.count())
            .where(ActionCentreItemRow.status == ActionItemStatus.PENDING.value)
            .group_by(ActionCentreItemRow.workflow)
        )
        return {workflow: int(count) for workflow, count in result.all()}

    async def oldest_pending_at_by_workflow(self) -> dict[str, datetime]:
        result = await self._session.execute(
            select(ActionCentreItemRow.workflow, func.min(ActionCentreItemRow.created_at))
            .where(ActionCentreItemRow.status == ActionItemStatus.PENDING.value)
            .group_by(ActionCentreItemRow.workflow)
        )
        return {workflow: oldest for workflow, oldest in result.all() if oldest is not None}

    async def list_for_workflow(
        self,
        workflow: str,
        *,
        status: str | None = None,
    ) -> list[ActionItem]:
        query = select(ActionCentreItemRow).where(ActionCentreItemRow.workflow == workflow)
        if status is not None:
            query = query.where(ActionCentreItemRow.status == status)
        rows = await self._session.scalars(query.order_by(ActionCentreItemRow.created_at))
        return [
            ActionItem(
                workflow=row.workflow,
                entity_id=row.entity_id,
                status=ActionItemStatus(row.status),
                created_at=row.created_at,
                metadata=dict(row.item_metadata or {}),
                resolved_at=row.resolved_at,
            )
            for row in rows
        ]

    async def _get(self, workflow: str, entity_id: str) -> ActionCentreItemRow | None:
        return await self._session.get(ActionCentreItemRow, (workflow, entity_id))


_CURSOR_NAME = "action_centre_projector"


class SqlAlchemyProcessedOutboxCursor:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_last_processed_id(self) -> str | None:
        row = await self._session.get(ActionCentreOutboxCursorRow, _CURSOR_NAME)
        return row.last_processed_outbox_id if row else None

    async def set_last_processed_id(self, outbox_id: str) -> None:
        row = await self._session.get(ActionCentreOutboxCursorRow, _CURSOR_NAME)
        now = timeutils.datetime_now()
        if row is None:
            self._session.add(
                ActionCentreOutboxCursorRow(
                    name=_CURSOR_NAME,
                    last_processed_outbox_id=outbox_id,
                    updated_at=now,
                )
            )
            return
        row.last_processed_outbox_id = outbox_id
        row.updated_at = now


class SqlAlchemyOutboxEventReader:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_after(
        self,
        *,
        cursor_id: str | None,
        types: list[str],
        limit: int,
    ) -> list[DomainEventOutboxRow]:
        query = select(DomainEventOutboxRow).where(DomainEventOutboxRow.type.in_(types))
        if cursor_id is not None:
            query = query.where(DomainEventOutboxRow.id > cursor_id)
        rows = await self._session.scalars(query.order_by(DomainEventOutboxRow.id).limit(limit))
        return list(rows)
