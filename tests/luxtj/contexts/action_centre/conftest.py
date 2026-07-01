import pytest

from luxtj.contexts.action_centre.application.use_cases import ActionCentreService
from luxtj.contexts.action_centre.infrastructure.persistence.in_memory import (
    InMemoryActionItemRepository,
)


@pytest.fixture
def action_centre_repo() -> InMemoryActionItemRepository:
    return InMemoryActionItemRepository()


@pytest.fixture
def action_centre_service(action_centre_repo) -> ActionCentreService:
    return ActionCentreService(repository=action_centre_repo)
