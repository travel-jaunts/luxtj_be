from typing import Annotated

from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.bootstrap import config
from luxtj.contexts.customer.application.bucket_list_recommendation_engine.providers.interfaces import (
    FlightInventoryProvider,
    HotelInventoryProvider,
)
from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.providers.interfaces import (
    DealInventoryProvider,
)
from luxtj.contexts.customer.application.ports import (
    BucketListRepository,
    DestinationSuggestionProvider,
    PersonalCalendarRepository,
)
from luxtj.contexts.customer.application.use_cases import (
    AddBucketListItem,
    AddPersonalCalendarEvent,
    AddPersonalCalendarPeriod,
    DeleteBucketListItem,
    GetBucketList,
    GetPersonalCalendarConsolidatedView,
    GetPersonalCalendarHolidayTypes,
    RecommendBucketListDeals,
    RecommendPersonalCalendarDeals,
    SuggestDestinations,
    UpdateBucketListItem,
)
from luxtj.contexts.customer.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyBucketListRepository,
    SqlAlchemyPersonalCalendarRepository,
)
from luxtj.contexts.customer.infrastructure.personal_calendar_recommendations.deal_inventory_provider import (
    PendingPersonalCalendarDealInventoryProvider,
)
from luxtj.contexts.customer.infrastructure.recommendations.flight_inventory_provider import (
    PendingFlightInventoryProvider,
)
from luxtj.contexts.customer.infrastructure.recommendations.hotel_inventory_provider import (
    PendingHotelInventoryProvider,
)
from luxtj.contexts.customer.infrastructure.suggestions.third_party_provider import (
    ThirdPartyDestinationSuggestionProvider,
)
from luxtj.shared_kernel.application.event_bus import DomainEventPublisher
from luxtj.shared_kernel.infrastructure.events.outbox import OutboxEventPublisher
from luxtj.shared_kernel.presentation.http.dependencies import (
    database_session_handle,
    http_client_handle,
)


def build_bucket_list_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> BucketListRepository:
    return SqlAlchemyBucketListRepository(session)


def build_personal_calendar_repository(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> PersonalCalendarRepository:
    return SqlAlchemyPersonalCalendarRepository(session)


def build_outbox_event_publisher(
    session: Annotated[AsyncSession, Depends(database_session_handle)],
) -> DomainEventPublisher:
    return OutboxEventPublisher(session)


def build_destination_suggestion_provider(
    http_client: Annotated[AsyncClient, Depends(http_client_handle)],
) -> DestinationSuggestionProvider:
    return ThirdPartyDestinationSuggestionProvider(
        http_client=http_client,
        base_url=config.BUCKET_LIST_SUGGESTIONS_BASE_URL,
        api_key=config.BUCKET_LIST_SUGGESTIONS_API_KEY,
    )


def build_flight_inventory_provider() -> FlightInventoryProvider:
    return PendingFlightInventoryProvider()


def build_hotel_inventory_provider() -> HotelInventoryProvider:
    return PendingHotelInventoryProvider()


def build_personal_calendar_deal_inventory_provider() -> DealInventoryProvider:
    return PendingPersonalCalendarDealInventoryProvider()


def build_add_bucket_list_item(
    repository: Annotated[BucketListRepository, Depends(build_bucket_list_repository)],
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
) -> AddBucketListItem:
    return AddBucketListItem(repository=repository, event_publisher=event_publisher)


def build_update_bucket_list_item(
    repository: Annotated[BucketListRepository, Depends(build_bucket_list_repository)],
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
) -> UpdateBucketListItem:
    return UpdateBucketListItem(repository=repository, event_publisher=event_publisher)


def build_delete_bucket_list_item(
    repository: Annotated[BucketListRepository, Depends(build_bucket_list_repository)],
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
) -> DeleteBucketListItem:
    return DeleteBucketListItem(repository=repository, event_publisher=event_publisher)


def build_get_bucket_list(
    repository: Annotated[BucketListRepository, Depends(build_bucket_list_repository)],
) -> GetBucketList:
    return GetBucketList(repository=repository)


def build_recommend_bucket_list_deals(
    repository: Annotated[BucketListRepository, Depends(build_bucket_list_repository)],
    flight_provider: Annotated[
        FlightInventoryProvider,
        Depends(build_flight_inventory_provider),
    ],
    hotel_provider: Annotated[
        HotelInventoryProvider,
        Depends(build_hotel_inventory_provider),
    ],
) -> RecommendBucketListDeals:
    return RecommendBucketListDeals(
        repository=repository,
        flight_provider=flight_provider,
        hotel_provider=hotel_provider,
    )


def build_suggest_destinations(
    provider: Annotated[
        DestinationSuggestionProvider,
        Depends(build_destination_suggestion_provider),
    ],
    event_publisher: Annotated[DomainEventPublisher, Depends(build_outbox_event_publisher)],
) -> SuggestDestinations:
    return SuggestDestinations(provider=provider, event_publisher=event_publisher)


def build_add_personal_calendar_event(
    repository: Annotated[PersonalCalendarRepository, Depends(build_personal_calendar_repository)],
) -> AddPersonalCalendarEvent:
    return AddPersonalCalendarEvent(repository=repository)


def build_add_personal_calendar_period(
    repository: Annotated[PersonalCalendarRepository, Depends(build_personal_calendar_repository)],
) -> AddPersonalCalendarPeriod:
    return AddPersonalCalendarPeriod(repository=repository)


def build_get_personal_calendar_holiday_types() -> GetPersonalCalendarHolidayTypes:
    return GetPersonalCalendarHolidayTypes()


def build_get_personal_calendar_consolidated_view(
    repository: Annotated[PersonalCalendarRepository, Depends(build_personal_calendar_repository)],
) -> GetPersonalCalendarConsolidatedView:
    return GetPersonalCalendarConsolidatedView(repository=repository)


def build_recommend_personal_calendar_deals(
    repository: Annotated[PersonalCalendarRepository, Depends(build_personal_calendar_repository)],
    inventory_provider: Annotated[
        DealInventoryProvider,
        Depends(build_personal_calendar_deal_inventory_provider),
    ],
) -> RecommendPersonalCalendarDeals:
    return RecommendPersonalCalendarDeals(
        repository=repository,
        inventory_provider=inventory_provider,
    )
