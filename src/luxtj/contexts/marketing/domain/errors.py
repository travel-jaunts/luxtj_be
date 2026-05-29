class MarketingDomainError(Exception):
    pass


class CampaignPolicyViolation(MarketingDomainError):
    pass


class StartDateInPastError(CampaignPolicyViolation):
    pass


class RecurringScheduleRequiredError(CampaignPolicyViolation):
    pass


class InvalidCronExpressionError(CampaignPolicyViolation):
    pass
