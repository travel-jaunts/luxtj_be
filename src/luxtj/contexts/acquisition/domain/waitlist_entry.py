from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid7

from luxtj.contexts.acquisition.domain.enums import WaitlistStatus
from luxtj.contexts.acquisition.domain.value_objects import AcquisitionContext, Email
from luxtj.shared_kernel.domain.events import BaseDomainEvent
from luxtj.utils import timeutils


@dataclass
class WaitlistEntry:
    id: UUID
    name: str
    email: Email
    status: WaitlistStatus
    source: str | None
    referral_code: str | None
    acquisition_context: AcquisitionContext
    registered_at: datetime
    _events: list[BaseDomainEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def register(
        cls,
        *,
        name: str,
        email: Email,
        source: str | None,
        referral_code: str | None,
        acquisition_context: AcquisitionContext,
    ) -> WaitlistEntry:
        from luxtj.contexts.acquisition.domain.events import WaitlistEntryRegistered

        entry = cls(
            id=uuid7(),
            name=name,
            email=email,
            status=WaitlistStatus.PENDING,
            source=source,
            referral_code=referral_code,
            acquisition_context=acquisition_context,
            registered_at=timeutils.datetime_now(),
        )
        entry.record_event(WaitlistEntryRegistered.from_entry(entry))
        return entry

    def record_event(self, event: BaseDomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[BaseDomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
