class MarketingDomainError(Exception):
    pass


class CampaignPolicyViolationError(MarketingDomainError):
    pass


class StartDateInPastError(CampaignPolicyViolationError):
    pass


class RecurringScheduleRequiredError(CampaignPolicyViolationError):
    pass


class InvalidCronExpressionError(CampaignPolicyViolationError):
    pass
