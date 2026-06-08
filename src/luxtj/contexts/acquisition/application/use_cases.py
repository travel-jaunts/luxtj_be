from dataclasses import dataclass
from uuid import UUID

from luxtj.contexts.acquisition.application.commands import RegisterWaitlistEntryCommand
from luxtj.contexts.acquisition.application.ports import WaitlistEntryRepository
from luxtj.contexts.acquisition.domain.errors import DuplicateEmailError
from luxtj.contexts.acquisition.domain.waitlist_entry import WaitlistEntry
from luxtj.shared_kernel.application import DomainEventPublisher


@dataclass(frozen=True)
class WaitlistEntryDTO:
    id: UUID
    name: str
    email: str
    status: str

    @classmethod
    def from_domain(cls, entry: WaitlistEntry) -> WaitlistEntryDTO:
        return cls(
            id=entry.id,
            name=entry.name,
            email=entry.email.value,
            status=entry.status.value,
        )


class RegisterWaitlistEntry:
    def __init__(
        self,
        repository: WaitlistEntryRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self.repository = repository
        self.event_publisher = event_publisher

    async def __call__(self, command: RegisterWaitlistEntryCommand) -> WaitlistEntryDTO:
        existing = await self.repository.get_by_email(command.email.value)
        if existing is not None:
            raise DuplicateEmailError(f"Email {command.email.value!r} is already on the waitlist.")

        entry = WaitlistEntry.register(
            name=command.name,
            email=command.email,
            source=command.source,
            referral_code=command.referral_code,
            acquisition_context=command.acquisition_context,
        )
        await self.repository.add(entry)

        for event in entry.pull_events():
            await self.event_publisher.publish(event)

        return WaitlistEntryDTO.from_domain(entry)
