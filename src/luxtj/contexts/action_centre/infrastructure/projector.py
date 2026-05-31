from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from luxtj.contexts.action_centre.domain.events import (
    PENDING_EVENT_TYPE,
    RESOLVED_EVENT_TYPE,
)
from luxtj.contexts.action_centre.infrastructure.persistence import (
    SqlAlchemyActionItemRepository,
    SqlAlchemyOutboxEventReader,
    SqlAlchemyProcessedOutboxCursor,
)
from luxtj.shared_kernel.infrastructure.persistence.sqlalchemy import (
    AsyncSessionFactory,
    session_scope,
)
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)

PROJECTED_TYPES: list[str] = [PENDING_EVENT_TYPE, RESOLVED_EVENT_TYPE]


class ActionCentreOutboxProjector:
    """Polls the shared domain_event_outbox table for action_centre.* events and projects
    them into action_centre_items. Tracks its own cursor so other subscribers are unaffected."""

    def __init__(
        self,
        session_factory: AsyncSessionFactory,
        *,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 100,
    ):
        self._session_factory = session_factory
        self._poll_interval_seconds = poll_interval_seconds
        self._batch_size = batch_size
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = await self.tick()
                if processed == 0:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._poll_interval_seconds,
                    )
            except TimeoutError:
                continue
            except Exception as ex:
                logger.exception("ActionCentreOutboxProjector tick failed: %s", ex)
                await asyncio.sleep(self._poll_interval_seconds)

    async def tick(self) -> int:
        """Process one batch. Returns the number of events handled."""
        async with session_scope(self._session_factory) as session:
            reader = SqlAlchemyOutboxEventReader(session)
            cursor = SqlAlchemyProcessedOutboxCursor(session)
            repository = SqlAlchemyActionItemRepository(session)

            last_id = await cursor.get_last_processed_id()
            rows = await reader.fetch_after(
                cursor_id=last_id,
                types=PROJECTED_TYPES,
                limit=self._batch_size,
            )
            if not rows:
                return 0

            for row in rows:
                await _project_event(
                    repository=repository,
                    event_type=row.type,
                    payload=row.payload,
                    event_time=row.time,
                )
            await cursor.set_last_processed_id(rows[-1].id)
            return len(rows)


async def _project_event(
    *,
    repository: SqlAlchemyActionItemRepository,
    event_type: str,
    payload: dict[str, Any],
    event_time: datetime | None,
) -> None:
    data = payload.get("data") or {}
    workflow = data.get("workflow")
    entity_id = data.get("entity_id")
    if not workflow or not entity_id:
        logger.warning("Skipping malformed action_centre event: %s", payload.get("id"))
        return

    occurred_at = _resolve_occurred_at(data, event_time)
    metadata = data.get("metadata") or {}

    if event_type == PENDING_EVENT_TYPE:
        await repository.upsert_pending(
            workflow=workflow,
            entity_id=entity_id,
            occurred_at=occurred_at,
            metadata=metadata,
        )
    elif event_type == RESOLVED_EVENT_TYPE:
        await repository.mark_resolved(
            workflow=workflow,
            entity_id=entity_id,
            occurred_at=occurred_at,
        )


def _resolve_occurred_at(data: dict[str, Any], event_time: datetime | None) -> datetime:
    raw = data.get("occurred_at")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    if event_time is not None:
        return event_time
    return timeutils.datetime_now()
