from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.acquisition.domain.waitlist_entry import WaitlistEntry
from luxtj.contexts.acquisition.infrastructure.persistence.sqlalchemy_models import WaitlistEntryRow


class SqlAlchemyWaitlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entry: WaitlistEntry) -> None:
        self.session.add(WaitlistEntryRow.from_domain(entry))

    async def get_by_email(self, email: str) -> WaitlistEntry | None:
        row = await self.session.scalar(
            select(WaitlistEntryRow).where(WaitlistEntryRow.email == email)
        )
        return row.to_domain() if row is not None else None
