import asyncio
from abc import ABC, abstractmethod

from luxtj.shared_kernel.application.event_bus import DomainEventPublisher
from luxtj.shared_kernel.domain.events import BaseDomainEvent


class BaseInProcessEventSubscriber(ABC):
    """Base worker that periodically polls the in-process queue."""

    def __init__(
        self,
        event_publisher: InProcessEventPublisher,
        poll_interval_seconds: float = 1.0,
    ):
        self.event_publisher = event_publisher
        self.poll_interval_seconds = poll_interval_seconds
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
                event = await asyncio.wait_for(
                    self.event_publisher.event_queue.get(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                await self.on_idle()
                continue

            try:
                await self.handle_event(event)
            except Exception as ex:
                await self.on_error(event, ex)
            finally:
                self.event_publisher.event_queue.task_done()

    async def on_idle(self) -> None:
        """Hook invoked when no event is found within poll interval."""
        return None

    async def on_error(self, event: BaseDomainEvent, ex: Exception) -> None:
        print(f"Error while handling event {event.id}: {ex}")

    @abstractmethod
    async def handle_event(self, event: BaseDomainEvent) -> None:
        """Handle one domain event from the queue."""


class InProcessEventPublisher(DomainEventPublisher):
    def __init__(self):
        self.event_queue = asyncio.Queue[BaseDomainEvent](maxsize=100)

    async def publish(self, event: BaseDomainEvent) -> None:
        await self.event_queue.put(event)


class PrintInProcessEventSubscriber(BaseInProcessEventSubscriber):
    """Reference subscriber that prints events from the in-process queue."""

    async def handle_event(self, event: BaseDomainEvent) -> None:
        print(f"[DomainEvent] {event.model_dump_json()}")
