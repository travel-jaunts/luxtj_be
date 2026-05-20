from typing import Protocol

from luxtj.domain.event.base import BaseDomainEvent


class IDomainEventPublisher(Protocol):
    async def publish(self, event: BaseDomainEvent) -> None:
        """Publish a domain event to the appropriate handlers."""
        ...
