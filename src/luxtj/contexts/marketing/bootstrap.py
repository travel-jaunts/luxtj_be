from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.marketing.application.ports import (
    AudienceResolver,
    MarketingRepository,
    OfferRepository,
)
from luxtj.contexts.marketing.application.use_cases import MarketingService, OffersService
from luxtj.contexts.marketing.infrastructure.persistence.in_memory import (
    MockMarketingAudienceResolver,
)
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyMarketingRepository,
    SqlAlchemyOfferRepository,
)
from luxtj.shared_kernel.application.event_bus import DomainEventPublisher
from luxtj.shared_kernel.infrastructure.events.outbox import OutboxEventPublisher
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
)

_AUDIENCE_RESOLVER = MockMarketingAudienceResolver()


def build_marketing_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> MarketingRepository:
    return SqlAlchemyMarketingRepository(session)


def build_outbox_event_publisher(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> DomainEventPublisher:
    return OutboxEventPublisher(session)


def build_marketing_audience_resolver() -> AudienceResolver:
    return _AUDIENCE_RESOLVER


def build_marketing_service(
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
    marketing_repository: Annotated[MarketingRepository, Depends(build_marketing_repository)],
    audience_resolver: Annotated[AudienceResolver, Depends(build_marketing_audience_resolver)],
) -> MarketingService:
    return MarketingService(
        marketing_repository=marketing_repository,
        event_publisher=event_publisher,
        audience_resolver=audience_resolver,
    )


def build_offer_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> OfferRepository:
    return SqlAlchemyOfferRepository(session)


def build_offers_service(
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
    offer_repository: Annotated[OfferRepository, Depends(build_offer_repository)],
) -> OffersService:
    return OffersService(
        repository=offer_repository,
        event_publisher=event_publisher,
    )
