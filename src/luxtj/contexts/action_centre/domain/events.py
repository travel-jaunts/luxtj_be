from datetime import datetime
from typing import Any

from luxtj.shared_kernel.domain.events import BaseDomainEvent
from luxtj.utils import timeutils


class ActionCentreItemPending(BaseDomainEvent):
    source: str = "/luxtj/contexts/action_centre/domain/item"
    type: str = "com.luxtj.action_centre.item.pending.v1"
    datacontenttype: str | None = "application/json"

    @classmethod
    def for_entity(
        cls,
        *,
        workflow: str,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> ActionCentreItemPending:
        when = occurred_at or timeutils.datetime_now()
        return cls(
            subject=entity_id,
            time=when,
            data={
                "workflow": workflow,
                "entity_id": entity_id,
                "occurred_at": when.isoformat(),
                "metadata": metadata or {},
            },
        )


class ActionCentreItemResolved(BaseDomainEvent):
    source: str = "/luxtj/contexts/action_centre/domain/item"
    type: str = "com.luxtj.action_centre.item.resolved.v1"
    datacontenttype: str | None = "application/json"

    @classmethod
    def for_entity(
        cls,
        *,
        workflow: str,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> ActionCentreItemResolved:
        when = occurred_at or timeutils.datetime_now()
        return cls(
            subject=entity_id,
            time=when,
            data={
                "workflow": workflow,
                "entity_id": entity_id,
                "occurred_at": when.isoformat(),
                "metadata": metadata or {},
            },
        )


PENDING_EVENT_TYPE = ActionCentreItemPending.model_fields["type"].default
RESOLVED_EVENT_TYPE = ActionCentreItemResolved.model_fields["type"].default
