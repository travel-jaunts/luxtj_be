from dataclasses import dataclass

from luxtj.contexts.acquisition.domain.value_objects import AcquisitionContext, Email


@dataclass(frozen=True)
class RegisterWaitlistEntryCommand:
    name: str
    email: Email
    source: str | None
    referral_code: str | None
    acquisition_context: AcquisitionContext
