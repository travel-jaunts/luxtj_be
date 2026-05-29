import os

import pytest

from luxtj.shared_kernel.domain.events import BaseDomainEvent


def pytest_configure(config):
    # Provide a safe default so importing luxtj.bootstrap.config never raises KeyError.
    # Tests that actually exercise the database override this via .dev.env or monkeypatch.
    os.environ.setdefault("LTJBE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


class CapturingEventPublisher:
    """Fake event publisher that collects published events in memory for assertion."""

    def __init__(self) -> None:
        self.events: list[BaseDomainEvent] = []

    async def publish(self, event: BaseDomainEvent) -> None:
        self.events.append(event)

    def of_type(self, event_type: str) -> list[BaseDomainEvent]:
        return [e for e in self.events if e.type == event_type]

    def clear(self) -> None:
        self.events.clear()


@pytest.fixture
def event_publisher() -> CapturingEventPublisher:
    return CapturingEventPublisher()
