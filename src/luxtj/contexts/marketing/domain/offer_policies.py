from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from luxtj.contexts.marketing.domain.enums import OfferTypeEnum
from luxtj.contexts.marketing.domain.errors import OfferPolicyViolationError


@dataclass(frozen=True)
class OfferCreationContext:
    validity_start: datetime
    validity_end: datetime
    discount_value: float
    offer_type: OfferTypeEnum


class OfferPolicy(ABC):
    @abstractmethod
    def enforce(self, ctx: OfferCreationContext) -> None: ...


class ValidityDatesPolicy(OfferPolicy):
    def enforce(self, ctx: OfferCreationContext) -> None:
        now = datetime.now(tz=ctx.validity_start.tzinfo)
        if ctx.validity_start <= now:
            raise OfferPolicyViolationError(
                f"validity_start must be in the future, got {ctx.validity_start}"
            )
        if ctx.validity_end <= ctx.validity_start:
            raise OfferPolicyViolationError("validity_end must be after validity_start")


class DiscountValuePolicy(OfferPolicy):
    def enforce(self, ctx: OfferCreationContext) -> None:
        if ctx.discount_value <= 0:
            raise OfferPolicyViolationError(
                f"discount_value must be positive, got {ctx.discount_value}"
            )
        if ctx.offer_type == OfferTypeEnum.PERCENTAGE_OFF and ctx.discount_value > 100:
            raise OfferPolicyViolationError(
                f"discount_value for percentage_off cannot exceed 100, got {ctx.discount_value}"
            )


class OfferCreationPolicies:
    _policies: tuple[OfferPolicy, ...] = (
        ValidityDatesPolicy(),
        DiscountValuePolicy(),
    )

    def enforce_all(self, ctx: OfferCreationContext) -> None:
        for policy in self._policies:
            policy.enforce(ctx)


offer_creation_policies = OfferCreationPolicies()
