from typing import Protocol

from luxtj.contexts.acquisition.domain.waitlist_entry import WaitlistEntry


class WaitlistEntryRepository(Protocol):
    async def add(self, entry: WaitlistEntry) -> None: ...
    async def get_by_email(self, email: str) -> WaitlistEntry | None: ...
