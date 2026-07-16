from uuid import UUID, uuid7

import pytest

from luxtj.contexts.customer.application.ports import (
    BucketListRepository,
    DestinationSuggestion,
    DestinationSuggestionProvider,
    DestinationSuggestionResult,
    PersonalCalendarRepository,
)
from luxtj.contexts.customer.domain.bucket_list import BucketList
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.contexts.customer.domain.personal_calendar import PersonalCalendar


class InMemoryBucketListRepository(BucketListRepository):
    def __init__(self) -> None:
        self._by_account_id: dict[UUID, BucketList] = {}

    async def get_by_account_id(self, account_id: UUID) -> BucketList | None:
        return self._by_account_id.get(account_id)

    async def add(self, bucket_list: BucketList) -> None:
        self._by_account_id[bucket_list.account_id] = bucket_list

    async def save(self, bucket_list: BucketList) -> None:
        self._by_account_id[bucket_list.account_id] = bucket_list


class InMemoryPersonalCalendarRepository(PersonalCalendarRepository):
    def __init__(self) -> None:
        self._by_account_id: dict[UUID, PersonalCalendar] = {}

    async def get_by_account_id(self, account_id: UUID) -> PersonalCalendar | None:
        return self._by_account_id.get(account_id)

    async def add(self, calendar: PersonalCalendar) -> None:
        self._by_account_id[calendar.account_id] = calendar

    async def save(self, calendar: PersonalCalendar) -> None:
        self._by_account_id[calendar.account_id] = calendar


class StubThirdPartySuggestionProvider(DestinationSuggestionProvider):
    async def suggest(
        self,
        *,
        query: str,
        selected_kind: BucketDestinationKindEnum,
        selected_name: str | None,
    ) -> DestinationSuggestionResult:
        if selected_kind == BucketDestinationKindEnum.COUNTRY:
            selected = DestinationSuggestion(
                destination_kind=BucketDestinationKindEnum.CITY,
                destination_name="Paris",
                parent_country=query,
                ideal_days=4,
            )
            alternatives = [
                DestinationSuggestion(
                    destination_kind=BucketDestinationKindEnum.CITY,
                    destination_name="Lyon",
                    parent_country=query,
                    ideal_days=2,
                ),
                DestinationSuggestion(
                    destination_kind=BucketDestinationKindEnum.PLACE,
                    destination_name="French Riviera",
                    parent_country=query,
                    ideal_days=3,
                ),
            ]
            return DestinationSuggestionResult(selected=selected, alternatives=alternatives)

        selected = DestinationSuggestion(
            destination_kind=selected_kind,
            destination_name=selected_name or query,
            parent_country="France",
            ideal_days=3,
        )
        alternatives = [
            DestinationSuggestion(
                destination_kind=BucketDestinationKindEnum.CITY,
                destination_name="Nice",
                parent_country="France",
                ideal_days=2,
            )
        ]
        return DestinationSuggestionResult(selected=selected, alternatives=alternatives)


@pytest.fixture
def customer_account_id() -> UUID:
    return uuid7()


@pytest.fixture
def bucket_list_repository() -> InMemoryBucketListRepository:
    return InMemoryBucketListRepository()


@pytest.fixture
def personal_calendar_repository() -> InMemoryPersonalCalendarRepository:
    return InMemoryPersonalCalendarRepository()


@pytest.fixture
def suggestion_provider() -> StubThirdPartySuggestionProvider:
    return StubThirdPartySuggestionProvider()
