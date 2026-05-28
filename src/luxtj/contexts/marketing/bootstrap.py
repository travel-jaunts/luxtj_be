from typing import Annotated

from fastapi import Depends

from common.injectorlib import domain_event_publisher_handle
from luxtj.contexts.marketing.application.ports import AudienceResolver, MarketingRepository
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.infrastructure.persistence import (
    InMemoryMarketingRepository,
    MockMarketingAudienceResolver,
)
from luxtj.shared_kernel.application import DomainEventPublisher

_MARKETING_REPOSITORY = InMemoryMarketingRepository()
_AUDIENCE_RESOLVER = MockMarketingAudienceResolver()


def build_marketing_repository() -> MarketingRepository:
    return _MARKETING_REPOSITORY


def build_marketing_audience_resolver() -> AudienceResolver:
    return _AUDIENCE_RESOLVER


def build_marketing_service(
    event_publisher: Annotated[DomainEventPublisher, Depends(domain_event_publisher_handle)],
    marketing_repository: Annotated[MarketingRepository, Depends(build_marketing_repository)],
    audience_resolver: Annotated[AudienceResolver, Depends(build_marketing_audience_resolver)],
) -> MarketingService:
    return MarketingService(
        marketing_repository=marketing_repository,
        event_publisher=event_publisher,
        audience_resolver=audience_resolver,
    )
