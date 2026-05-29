from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.shared_kernel.domain.events import BaseDomainEvent
from luxtj.shared_kernel.infrastructure.persistence.outbox_model import DomainEventOutboxRow


class OutboxEventPublisher:
    """Writes domain events to the outbox table within the caller's DB transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def publish(self, event: BaseDomainEvent) -> None:
        self._session.add(DomainEventOutboxRow.from_event(event))
