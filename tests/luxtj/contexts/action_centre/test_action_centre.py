"""Action Centre application + projector tests."""

from datetime import UTC, datetime, timedelta

from luxtj.contexts.action_centre.application.use_cases import ActionCentreService
from luxtj.contexts.action_centre.domain.enums import ActionItemStatus
from luxtj.contexts.action_centre.infrastructure.persistence import InMemoryActionItemRepository


async def test_summary_lists_all_registered_workflows_even_when_empty(
    action_centre_service: ActionCentreService,
) -> None:
    summary = await action_centre_service.get_summary()
    workflows = [card.workflow for card in summary.cards]
    assert "kyc_approval" in workflows
    assert "content_review" in workflows
    for card in summary.cards:
        assert card.count == 0
        assert card.oldest_pending_at is None
        assert card.filter == {"status": "pending"}


async def test_summary_aggregates_pending_counts(
    action_centre_service: ActionCentreService,
    action_centre_repo: InMemoryActionItemRepository,
) -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval", entity_id="k1", occurred_at=now, metadata={}
    )
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval", entity_id="k2", occurred_at=now + timedelta(minutes=5), metadata={}
    )
    await action_centre_repo.upsert_pending(
        workflow="content_review",
        entity_id="c1",
        occurred_at=now + timedelta(minutes=1),
        metadata={},
    )

    summary = await action_centre_service.get_summary()
    by_workflow = {card.workflow: card for card in summary.cards}
    assert by_workflow["kyc_approval"].count == 2
    assert by_workflow["kyc_approval"].oldest_pending_at == now
    assert by_workflow["content_review"].count == 1


async def test_resolved_items_excluded_from_count(
    action_centre_service: ActionCentreService,
    action_centre_repo: InMemoryActionItemRepository,
) -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval", entity_id="k1", occurred_at=now, metadata={}
    )
    await action_centre_repo.mark_resolved(
        workflow="kyc_approval", entity_id="k1", occurred_at=now + timedelta(minutes=1)
    )

    summary = await action_centre_service.get_summary()
    by_workflow = {card.workflow: card for card in summary.cards}
    assert by_workflow["kyc_approval"].count == 0


async def test_duplicate_pending_event_is_idempotent(
    action_centre_repo: InMemoryActionItemRepository,
) -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval", entity_id="k1", occurred_at=now, metadata={"a": 1}
    )
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval",
        entity_id="k1",
        occurred_at=now + timedelta(minutes=5),
        metadata={"a": 2},
    )

    items = await action_centre_repo.list_for_workflow("kyc_approval")
    assert len(items) == 1
    assert items[0].status == ActionItemStatus.PENDING
    assert items[0].created_at == now


async def test_resolved_before_pending_creates_resolved_row(
    action_centre_repo: InMemoryActionItemRepository,
) -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    await action_centre_repo.mark_resolved(workflow="kyc_approval", entity_id="k1", occurred_at=now)
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval", entity_id="k1", occurred_at=now - timedelta(minutes=5), metadata={}
    )

    items = await action_centre_repo.list_for_workflow("kyc_approval")
    assert len(items) == 1
    assert items[0].status == ActionItemStatus.RESOLVED


async def test_duplicate_resolved_event_is_idempotent(
    action_centre_repo: InMemoryActionItemRepository,
) -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    await action_centre_repo.upsert_pending(
        workflow="kyc_approval", entity_id="k1", occurred_at=now, metadata={}
    )
    first_resolve = now + timedelta(minutes=1)
    await action_centre_repo.mark_resolved(
        workflow="kyc_approval", entity_id="k1", occurred_at=first_resolve
    )
    await action_centre_repo.mark_resolved(
        workflow="kyc_approval", entity_id="k1", occurred_at=now + timedelta(minutes=10)
    )

    items = await action_centre_repo.list_for_workflow("kyc_approval")
    assert items[0].resolved_at == first_resolve
