from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid7

from luxtj.contexts.marketing.domain.enums import OfferStatusEnum, OfferTypeEnum
from luxtj.contexts.marketing.domain.errors import OfferPolicyViolationError
from luxtj.contexts.marketing.domain.offer_policies import (
    OfferCreationContext,
    offer_creation_policies,
)
from luxtj.shared_kernel.domain import BaseDomainEvent
from luxtj.utils import timeutils


def _generate_code() -> str:
    return uuid7().hex[:8].upper()


@dataclass
class Offer:
    id: UUID
    name: str
    code: str
    type: OfferTypeEnum
    discount_value: float
    min_booking_value: float
    min_booking_value_currency: str
    validity_start: datetime
    validity_end: datetime
    usage_limit_per_user: int | None
    applicability_on: list[str]
    stackable: bool
    auto_apply: bool
    status: OfferStatusEnum
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    _events: list[BaseDomainEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        code: str | None,
        type: OfferTypeEnum,
        discount_value: float,
        min_booking_value: float,
        min_booking_value_currency: str,
        validity_start: datetime,
        validity_end: datetime,
        usage_limit_per_user: int | None,
        applicability_on: list[str],
        stackable: bool = False,
        auto_apply: bool = True,
    ) -> Offer:
        from luxtj.contexts.marketing.domain.events import OfferCreated

        offer_creation_policies.enforce_all(
            OfferCreationContext(
                validity_start=validity_start,
                validity_end=validity_end,
                discount_value=discount_value,
                offer_type=type,
            )
        )

        now = timeutils.datetime_now()
        offer = cls(
            id=uuid7(),
            name=name,
            code=code if code else _generate_code(),
            type=type,
            discount_value=discount_value,
            min_booking_value=min_booking_value,
            min_booking_value_currency=min_booking_value_currency,
            validity_start=validity_start,
            validity_end=validity_end,
            usage_limit_per_user=usage_limit_per_user,
            applicability_on=list(applicability_on),
            stackable=stackable,
            auto_apply=auto_apply,
            status=OfferStatusEnum.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        offer.record_event(OfferCreated.from_offer(offer))
        return offer

    def pause(self) -> None:
        from luxtj.contexts.marketing.domain.events import OfferPaused

        if self.status != OfferStatusEnum.ACTIVE:
            raise OfferPolicyViolationError(
                f"Only active offers can be paused, current status: {self.status}"
            )
        self.status = OfferStatusEnum.PAUSED
        self.updated_at = timeutils.datetime_now()
        self.record_event(OfferPaused.from_offer(self))

    def rescind(self) -> None:
        from luxtj.contexts.marketing.domain.events import OfferRescinded

        if self.status == OfferStatusEnum.DELETED:
            raise OfferPolicyViolationError("Cannot rescind a deleted offer")
        self.status = OfferStatusEnum.RESCINDED
        self.updated_at = timeutils.datetime_now()
        self.record_event(OfferRescinded.from_offer(self))

    def delete(self) -> None:
        from luxtj.contexts.marketing.domain.events import OfferDeleted

        if self.status == OfferStatusEnum.DELETED:
            return
        now = timeutils.datetime_now()
        self.status = OfferStatusEnum.DELETED
        self.updated_at = now
        self.deleted_at = now
        self.record_event(OfferDeleted.from_offer(self))

    def record_event(self, event: BaseDomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[BaseDomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
