import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from luxtj.contexts.marketing.domain.enums import ScheduleFrequencyEnum
from luxtj.contexts.marketing.domain.errors import (
    InvalidCronExpressionError,
    RecurringScheduleRequiredError,
    StartDateInPastError,
)

# Matches a single cron field: digits, *, /, -, and , only.
_CRON_FIELD_RE = re.compile(r"^[\d*/,\-]+$")


def _is_valid_cron(expression: str) -> bool:
    fields = expression.strip().split()
    return len(fields) == 5 and all(_CRON_FIELD_RE.match(f) for f in fields)


@dataclass(frozen=True)
class CampaignCreationContext:
    """
    All data available to campaign creation policies.
    Add new fields here when new policies need to inspect additional creation inputs.
    """

    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None


class CampaignPolicy(ABC):
    """Base class for a single campaign creation rule."""

    @abstractmethod
    def enforce(self, ctx: CampaignCreationContext) -> None:
        """Raise CampaignPolicyViolationError if the policy is violated."""


class StartDatePolicy(CampaignPolicy):
    def enforce(self, ctx: CampaignCreationContext) -> None:
        if ctx.start_date < date.today():
            raise StartDateInPastError(
                f"start_date must be today or in the future, got {ctx.start_date}"
            )


class RecurringSchedulePolicy(CampaignPolicy):
    def enforce(self, ctx: CampaignCreationContext) -> None:
        if ctx.frequency != ScheduleFrequencyEnum.RECURRING:
            return
        if not ctx.frequency_schedule:
            raise RecurringScheduleRequiredError(
                "frequency_schedule is required when frequency is recurring"
            )
        if not _is_valid_cron(ctx.frequency_schedule):
            raise InvalidCronExpressionError(
                f"frequency_schedule must be a valid 5-field cron expression, got {ctx.frequency_schedule!r}"
            )


class CampaignCreationPolicies:
    """
    Composite that runs all creation policies in order.
    Register new policies by adding them to _policies.
    """

    _policies: tuple[CampaignPolicy, ...] = (
        StartDatePolicy(),
        RecurringSchedulePolicy(),
    )

    def enforce_all(self, ctx: CampaignCreationContext) -> None:
        for policy in self._policies:
            policy.enforce(ctx)


campaign_creation_policies = CampaignCreationPolicies()
