from typing import TYPE_CHECKING, Any

from pydantic import Field

from luxtj.shared_kernel.domain.events import BaseDomainEvent

if TYPE_CHECKING:
    from luxtj.contexts.acquisition.domain.waitlist_entry import WaitlistEntry


class WaitlistEntryRegistered(BaseDomainEvent):
    source: str = "/luxtj/contexts/acquisition/domain/waitlist_entry"
    type: str = "com.luxtj.acquisition.waitlist_entry.registered.v1"
    datacontenttype: str | None = "application/json"
    data: dict[str, Any] | None = Field(default=None)

    @classmethod
    def from_entry(cls, entry: WaitlistEntry) -> WaitlistEntryRegistered:
        return cls(
            subject=str(entry.id),
            time=entry.registered_at,
            data={
                "id": str(entry.id),
                "email": entry.email.value,
                "name": entry.name,
                "source": entry.source,
                "status": entry.status.value,
                "registered_at": entry.registered_at.isoformat(),
            },
        )
