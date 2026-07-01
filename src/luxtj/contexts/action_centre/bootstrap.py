from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.action_centre.application.ports import ActionItemRepository
from luxtj.contexts.action_centre.application.use_cases import ActionCentreService
from luxtj.contexts.action_centre.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyActionItemRepository,
)
from luxtj.shared_kernel.presentation.http.dependencies import database_session_handle


def build_action_item_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> ActionItemRepository:
    return SqlAlchemyActionItemRepository(session)


def build_action_centre_service(
    repository: Annotated[ActionItemRepository, Depends(build_action_item_repository)],
) -> ActionCentreService:
    return ActionCentreService(repository=repository)
