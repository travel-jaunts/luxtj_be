from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from luxtj.contexts.customer.application.bucket_list_recommendation_engine.engine import (
    recommend_bucket_list_deals,
)
from luxtj.contexts.customer.application.bucket_list_recommendation_engine.exceptions import (
    RecommendationEngineError,
)
from luxtj.contexts.customer.application.bucket_list_recommendation_engine.models import (
    BucketListRecommendationInput,
    BucketListRecommendationResult,
    Destination,
    Itinerary,
)
from luxtj.contexts.customer.application.bucket_list_recommendation_engine.providers.interfaces import (
    FlightInventoryProvider,
    HotelInventoryProvider,
)
from luxtj.contexts.customer.application.commands import (
    AddBucketListItemCommand,
    AddPersonalCalendarEventCommand,
    AddPersonalCalendarPeriodCommand,
    DeleteBucketListItemCommand,
    SuggestDestinationsCommand,
    UpdateBucketListItemCommand,
)
from luxtj.contexts.customer.application.ports import (
    BucketListRepository,
    DestinationSuggestion,
    DestinationSuggestionProvider,
    PersonalCalendarRepository,
)
from luxtj.contexts.customer.application.queries import (
    GetBucketListQuery,
    RecommendBucketListDealsQuery,
)
from luxtj.contexts.customer.domain.bucket_list import BucketList, BucketListItem
from luxtj.contexts.customer.domain.enums import HOLIDAY_TYPE_LIST, PersonalCalendarEventTypeEnum
from luxtj.contexts.customer.domain.errors import (
    BucketListRecommendationError,
    InvalidPersonalCalendarEventError,
)
from luxtj.contexts.customer.domain.events import DestinationSuggestionResolved
from luxtj.contexts.customer.domain.personal_calendar import (
    PersonalCalendar,
    PersonalCalendarEventItem,
    PersonalCalendarPeriodItem,
)
from luxtj.shared_kernel.application.event_bus import DomainEventPublisher


@dataclass(frozen=True)
class BucketListItemDTO:
    id: UUID
    destination_kind: str
    destination_name: str
    parent_country: str | None
    ideal_days: int
    display_order: int
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_domain(cls, item: BucketListItem) -> BucketListItemDTO:
        return cls(
            id=item.id,
            destination_kind=item.destination_kind.value,
            destination_name=item.destination_name,
            parent_country=item.parent_country,
            ideal_days=item.ideal_days,
            display_order=item.display_order,
            notes=item.notes,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted_at=item.deleted_at,
        )


@dataclass(frozen=True)
class BucketListDTO:
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[BucketListItemDTO]

    @classmethod
    def from_domain(cls, bucket_list: BucketList, *, include_deleted: bool) -> BucketListDTO:
        if include_deleted:
            items = sorted(
                bucket_list.items, key=lambda value: (value.display_order, value.created_at)
            )
        else:
            items = bucket_list.active_items()
        return cls(
            id=bucket_list.id,
            account_id=bucket_list.account_id,
            created_at=bucket_list.created_at,
            updated_at=bucket_list.updated_at,
            items=[BucketListItemDTO.from_domain(item) for item in items],
        )


@dataclass(frozen=True)
class DestinationSuggestionDTO:
    destination_kind: str
    destination_name: str
    parent_country: str | None
    ideal_days: int

    @classmethod
    def from_port(cls, suggestion: DestinationSuggestion) -> DestinationSuggestionDTO:
        return cls(
            destination_kind=suggestion.destination_kind.value,
            destination_name=suggestion.destination_name,
            parent_country=suggestion.parent_country,
            ideal_days=suggestion.ideal_days,
        )


@dataclass(frozen=True)
class DestinationSuggestionResultDTO:
    selected: DestinationSuggestionDTO
    alternatives: list[DestinationSuggestionDTO]


@dataclass(frozen=True)
class PersonalCalendarEventItemDTO:
    id: UUID
    event_type: str
    event_date: date
    holiday_types: list[str]
    birthday_for: str | None
    anniversary_for: str | None
    person_name: str | None
    person1_name: str | None
    person2_name: str | None
    event_name: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, item: PersonalCalendarEventItem) -> PersonalCalendarEventItemDTO:
        return cls(
            id=item.id,
            event_type=item.event_type.value,
            event_date=item.event_date,
            holiday_types=[value.value for value in item.holiday_types],
            birthday_for=item.birthday_for.value if item.birthday_for else None,
            anniversary_for=item.anniversary_for.value if item.anniversary_for else None,
            person_name=item.person_name,
            person1_name=item.person1_name,
            person2_name=item.person2_name,
            event_name=item.event_name,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


@dataclass(frozen=True)
class PersonalCalendarPeriodItemDTO:
    id: UUID
    period_name: str
    period_start: date
    period_end: date
    is_date_flexible: bool
    holiday_types: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, item: PersonalCalendarPeriodItem) -> PersonalCalendarPeriodItemDTO:
        return cls(
            id=item.id,
            period_name=item.period_name,
            period_start=item.period_start,
            period_end=item.period_end,
            is_date_flexible=item.is_date_flexible,
            holiday_types=[value.value for value in item.holiday_types],
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


@dataclass(frozen=True)
class HolidayTypeListDTO:
    holiday_types: list[str]


@dataclass(frozen=True)
class PersonalCalendarConsolidatedItemDTO:
    item_type: str
    start_date: date
    end_date: date | None
    event_type: str | None
    event_name: str | None
    period_name: str | None
    holiday_types: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PersonalCalendarConsolidatedViewDTO:
    account_id: UUID
    items: list[PersonalCalendarConsolidatedItemDTO]


class AddBucketListItem:
    def __init__(
        self,
        repository: BucketListRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    async def __call__(self, command: AddBucketListItemCommand) -> BucketListItemDTO:
        bucket_list = await self._load_or_create(command.account_id)
        item = bucket_list.add_item(
            destination_kind=command.destination_kind,
            destination_name=command.destination_name,
            parent_country=command.parent_country,
            ideal_days=command.ideal_days,
            display_order=command.display_order,
            notes=command.notes,
        )
        await self._repository.save(bucket_list)
        await self._flush_events(bucket_list)
        return BucketListItemDTO.from_domain(item)

    async def _load_or_create(self, account_id: UUID) -> BucketList:
        bucket_list = await self._repository.get_by_account_id(account_id)
        if bucket_list is None:
            bucket_list = BucketList.create(account_id=account_id)
            await self._repository.add(bucket_list)
        return bucket_list

    async def _flush_events(self, bucket_list: BucketList) -> None:
        for event in bucket_list.pull_events():
            await self._event_publisher.publish(event)


class UpdateBucketListItem:
    def __init__(
        self,
        repository: BucketListRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    async def __call__(self, command: UpdateBucketListItemCommand) -> BucketListItemDTO:
        bucket_list = await self._must_get(command.account_id)
        item = bucket_list.update_item(
            item_id=command.item_id,
            ideal_days=command.ideal_days,
            display_order=command.display_order,
            notes=command.notes,
        )
        await self._repository.save(bucket_list)
        await self._flush_events(bucket_list)
        return BucketListItemDTO.from_domain(item)

    async def _must_get(self, account_id: UUID) -> BucketList:
        bucket_list = await self._repository.get_by_account_id(account_id)
        if bucket_list is None:
            raise KeyError(str(account_id))
        return bucket_list

    async def _flush_events(self, bucket_list: BucketList) -> None:
        for event in bucket_list.pull_events():
            await self._event_publisher.publish(event)


class DeleteBucketListItem:
    def __init__(
        self,
        repository: BucketListRepository,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    async def __call__(self, command: DeleteBucketListItemCommand) -> BucketListItemDTO:
        bucket_list = await self._must_get(command.account_id)
        item = bucket_list.delete_item(item_id=command.item_id)
        await self._repository.save(bucket_list)
        await self._flush_events(bucket_list)
        return BucketListItemDTO.from_domain(item)

    async def _must_get(self, account_id: UUID) -> BucketList:
        bucket_list = await self._repository.get_by_account_id(account_id)
        if bucket_list is None:
            raise KeyError(str(account_id))
        return bucket_list

    async def _flush_events(self, bucket_list: BucketList) -> None:
        for event in bucket_list.pull_events():
            await self._event_publisher.publish(event)


class GetBucketList:
    def __init__(self, repository: BucketListRepository) -> None:
        self._repository = repository

    async def __call__(self, query: GetBucketListQuery) -> BucketListDTO:
        bucket_list = await self._repository.get_by_account_id(query.account_id)
        if bucket_list is None:
            bucket_list = BucketList.create(account_id=query.account_id)
        return BucketListDTO.from_domain(bucket_list, include_deleted=query.include_deleted)


class RecommendBucketListDeals:
    def __init__(
        self,
        repository: BucketListRepository,
        flight_provider: FlightInventoryProvider,
        hotel_provider: HotelInventoryProvider,
    ) -> None:
        self._repository = repository
        self._flight_provider = flight_provider
        self._hotel_provider = hotel_provider

    async def __call__(
        self, query: RecommendBucketListDealsQuery
    ) -> BucketListRecommendationResult:
        bucket_list = await self._repository.get_by_account_id(query.account_id)
        if bucket_list is None:
            raise BucketListRecommendationError(
                f"Bucket list for account {query.account_id} was not found"
            )

        active_items = bucket_list.active_items()
        if not active_items:
            raise BucketListRecommendationError(
                "At least one active bucket-list destination is required"
            )

        try:
            itinerary = Itinerary(
                destinations=[
                    Destination(name=item.destination_name, days=item.ideal_days)
                    for item in active_items
                ]
            )
            request = BucketListRecommendationInput(
                origin=query.origin,
                reference_date=query.reference_date,
                itinerary=itinerary,
            )
            return recommend_bucket_list_deals(
                request=request,
                flight_provider=self._flight_provider,
                hotel_provider=self._hotel_provider,
            )
        except RecommendationEngineError as exc:
            raise BucketListRecommendationError(str(exc)) from exc
        except ValueError as exc:
            raise BucketListRecommendationError(str(exc)) from exc


class SuggestDestinations:
    def __init__(
        self,
        provider: DestinationSuggestionProvider,
        event_publisher: DomainEventPublisher,
    ) -> None:
        self._provider = provider
        self._event_publisher = event_publisher

    async def __call__(self, command: SuggestDestinationsCommand) -> DestinationSuggestionResultDTO:
        suggestions = await self._provider.suggest(
            query=command.query,
            selected_kind=command.selected_kind,
            selected_name=command.selected_name,
        )
        await self._event_publisher.publish(
            DestinationSuggestionResolved.from_resolution(
                selected_kind=command.selected_kind,
                query=command.query,
                selected_name=command.selected_name,
                alternative_count=len(suggestions.alternatives),
            )
        )
        return DestinationSuggestionResultDTO(
            selected=DestinationSuggestionDTO.from_port(suggestions.selected),
            alternatives=[
                DestinationSuggestionDTO.from_port(item) for item in suggestions.alternatives
            ],
        )


class AddPersonalCalendarEvent:
    def __init__(self, repository: PersonalCalendarRepository) -> None:
        self._repository = repository

    async def __call__(
        self, command: AddPersonalCalendarEventCommand
    ) -> PersonalCalendarEventItemDTO:
        calendar = await self._load_or_create(command.account_id)

        if command.event_type == PersonalCalendarEventTypeEnum.BIRTHDAY:
            if command.birthday_for is None:
                raise InvalidPersonalCalendarEventError(
                    "birthday_for is required for birthday event"
                )
            item = calendar.add_birthday_event(
                birthday_for=command.birthday_for,
                person_name=command.person_name or "",
                event_date=command.event_date,
                holiday_types=command.holiday_types,
            )
        elif command.event_type == PersonalCalendarEventTypeEnum.ANNIVERSARY:
            if command.anniversary_for is None:
                raise InvalidPersonalCalendarEventError(
                    "anniversary_for is required for anniversary event"
                )
            item = calendar.add_anniversary_event(
                anniversary_for=command.anniversary_for,
                person1_name=command.person1_name or "",
                person2_name=command.person2_name or "",
                event_date=command.event_date,
                holiday_types=command.holiday_types,
            )
        else:
            item = calendar.add_special_occasion_event(
                event_name=command.event_name or "",
                event_date=command.event_date,
                holiday_types=command.holiday_types,
            )

        await self._repository.save(calendar)
        return PersonalCalendarEventItemDTO.from_domain(item)

    async def _load_or_create(self, account_id: UUID) -> PersonalCalendar:
        calendar = await self._repository.get_by_account_id(account_id)
        if calendar is None:
            calendar = PersonalCalendar.create(account_id=account_id)
            await self._repository.add(calendar)
        return calendar


class AddPersonalCalendarPeriod:
    def __init__(self, repository: PersonalCalendarRepository) -> None:
        self._repository = repository

    async def __call__(
        self, command: AddPersonalCalendarPeriodCommand
    ) -> PersonalCalendarPeriodItemDTO:
        calendar = await self._load_or_create(command.account_id)
        item = calendar.add_period(
            period_name=command.period_name,
            period_start=command.period_start,
            period_end=command.period_end,
            is_date_flexible=command.is_date_flexible,
            holiday_types=command.holiday_types,
        )
        await self._repository.save(calendar)
        return PersonalCalendarPeriodItemDTO.from_domain(item)

    async def _load_or_create(self, account_id: UUID) -> PersonalCalendar:
        calendar = await self._repository.get_by_account_id(account_id)
        if calendar is None:
            calendar = PersonalCalendar.create(account_id=account_id)
            await self._repository.add(calendar)
        return calendar


class GetPersonalCalendarHolidayTypes:
    async def __call__(self) -> HolidayTypeListDTO:
        return HolidayTypeListDTO(holiday_types=list(HOLIDAY_TYPE_LIST))


class GetPersonalCalendarConsolidatedView:
    def __init__(self, repository: PersonalCalendarRepository) -> None:
        self._repository = repository

    async def __call__(self, account_id: UUID) -> PersonalCalendarConsolidatedViewDTO:
        calendar = await self._repository.get_by_account_id(account_id)
        if calendar is None:
            calendar = PersonalCalendar.create(account_id=account_id)

        items: list[PersonalCalendarConsolidatedItemDTO] = []
        for event in calendar.events:
            items.append(
                PersonalCalendarConsolidatedItemDTO(
                    item_type="event",
                    start_date=event.event_date,
                    end_date=None,
                    event_type=event.event_type.value,
                    event_name=event.event_name
                    or event.person_name
                    or " & ".join(
                        value
                        for value in (event.person1_name, event.person2_name)
                        if value is not None
                    ),
                    period_name=None,
                    holiday_types=[value.value for value in event.holiday_types],
                    created_at=event.created_at,
                    updated_at=event.updated_at,
                )
            )

        for period in calendar.periods:
            items.append(
                PersonalCalendarConsolidatedItemDTO(
                    item_type="period",
                    start_date=period.period_start,
                    end_date=period.period_end,
                    event_type=None,
                    event_name=None,
                    period_name=period.period_name,
                    holiday_types=[value.value for value in period.holiday_types],
                    created_at=period.created_at,
                    updated_at=period.updated_at,
                )
            )

        sorted_items = sorted(items, key=lambda value: (value.start_date, value.created_at))
        return PersonalCalendarConsolidatedViewDTO(account_id=account_id, items=sorted_items)
