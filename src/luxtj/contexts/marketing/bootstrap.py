from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.injectorlib import database_session_handle, domain_event_publisher_handle
from luxtj.contexts.marketing.application.ports import AudienceResolver, MarketingRepository
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.infrastructure.persistence import (
    MockMarketingAudienceResolver,
    SqlAlchemyMarketingRepository,
)
from luxtj.shared_kernel.application import DomainEventPublisher

_AUDIENCE_RESOLVER = MockMarketingAudienceResolver()


def build_marketing_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> MarketingRepository:
    return SqlAlchemyMarketingRepository(session)


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
