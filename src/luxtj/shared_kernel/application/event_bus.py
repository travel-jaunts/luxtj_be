from typing import Protocol

from luxtj.shared_kernel.domain.events import BaseDomainEvent


class DomainEventPublisher(Protocol):
    async def publish(self, event: BaseDomainEvent) -> None:
        """Publish a domain event to the configured event transport."""
        ...
