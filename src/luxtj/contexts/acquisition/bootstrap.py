from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.acquisition.application.ports import WaitlistEntryRepository
from luxtj.contexts.acquisition.application.use_cases import RegisterWaitlistEntry
from luxtj.contexts.acquisition.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyWaitlistRepository,
)
from luxtj.shared_kernel.application.event_bus import DomainEventPublisher
from luxtj.shared_kernel.infrastructure.events.outbox import OutboxEventPublisher
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle


def build_waitlist_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> WaitlistEntryRepository:
    return SqlAlchemyWaitlistRepository(session)


def build_outbox_event_publisher(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> DomainEventPublisher:
    return OutboxEventPublisher(session)


def build_register_waitlist_entry(
    repository: Annotated[WaitlistEntryRepository, Depends(build_waitlist_repository)],
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
) -> RegisterWaitlistEntry:
    return RegisterWaitlistEntry(repository=repository, event_publisher=event_publisher)
