from luxtj.contexts.action_centre.application.ports import ActionItemRepository
from luxtj.contexts.action_centre.application.queries import Summary, SummaryCard
from luxtj.contexts.action_centre.domain.workflow_registry import get_registered_workflows
from luxtj.utils import timeutils


class ActionCentreService:
    def __init__(self, repository: ActionItemRepository):
        self._repository = repository

    async def get_summary(self) -> Summary:
        counts = await self._repository.count_pending_by_workflow()
        oldest = await self._repository.oldest_pending_at_by_workflow()

        cards: list[SummaryCard] = []
        for workflow in get_registered_workflows():
            cards.append(
                SummaryCard(
                    workflow=workflow.key,
                    label=workflow.label,
                    count=counts.get(workflow.key, 0),
                    oldest_pending_at=oldest.get(workflow.key),
                    filter={"status": "pending"},
                )
            )

        return Summary(cards=cards, generated_at=timeutils.datetime_now())
