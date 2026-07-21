from datetime import date
from decimal import Decimal
from uuid import uuid7

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from luxtj.contexts.customer.application.commands import AddPersonalCalendarEventCommand
from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.enums import (
    CalendarSourceType,
    CancellationPolicy,
    DealTier,
    PlanType,
    RecommendationStatus,
    TravelerType,
)
from luxtj.contexts.customer.application.personal_calendar_recommendation_engine.models import (
    DealCandidate,
    DealSearchRequest,
)
from luxtj.contexts.customer.application.queries import RecommendPersonalCalendarDealsQuery
from luxtj.contexts.customer.application.use_cases import (
    AddPersonalCalendarEvent,
    RecommendPersonalCalendarDeals,
)
from luxtj.contexts.customer.bootstrap import build_recommend_personal_calendar_deals
from luxtj.contexts.customer.domain.enums import (
    BirthdayForEnum,
    HolidayTypeEnum,
    PersonalCalendarEventTypeEnum,
)
from luxtj.contexts.customer.domain.errors import PersonalCalendarRecommendationItemNotFoundError
from luxtj.contexts.customer.presentation.http.router import customer_personal_calendar_router


class MatchingDealInventoryProvider:
    def __init__(self) -> None:
        self.requests: list[DealSearchRequest] = []

    async def search_deals(self, request: DealSearchRequest) -> tuple[DealCandidate, ...]:
        self.requests.append(request)
        quality = {
            DealTier.LITE: 4.2,
            DealTier.PLUS: 4.7,
            DealTier.ULTRA: 5.0,
        }[request.tier]
        return (
            DealCandidate(
                candidate_id=f"candidate-{len(self.requests)}",
                provider_id="test-provider",
                plan_type=request.plan_type,
                tier=request.tier,
                name="Edinburgh Celebration Stay",
                destination="Edinburgh",
                country="United Kingdom",
                city="Edinburgh",
                start_date=request.window.start_date,
                end_date=request.window.end_date,
                currency=request.pricing_currency,
                total_price=Decimal("900"),
                market_reference_price=Decimal("1200"),
                quality_rating=quality,
                review_count=500,
                cancellation_policy=CancellationPolicy.FREE_CANCELLATION,
                tags=("wellness", "signature experience"),
                suited_for=(
                    TravelerType.SOLO,
                    TravelerType.COUPLE,
                    TravelerType.FAMILY,
                ),
                family_friendly=True,
                maximum_travelers=6,
                rooms_included=3,
                supplier_reliability=0.95,
                supplier_complaint_ratio=0.02,
                refund_frequency=0.03,
                value_additions=("breakfast",),
            ),
        )


async def _add_birthday(repository, account_id):
    use_case = AddPersonalCalendarEvent(repository=repository)
    return await use_case(
        AddPersonalCalendarEventCommand(
            account_id=account_id,
            event_type=PersonalCalendarEventTypeEnum.BIRTHDAY,
            event_date=date(2026, 8, 10),
            holiday_types=[HolidayTypeEnum.WELLNESS_AND_SPA_RETREATS],
            birthday_for=BirthdayForEnum.MY_BIRTHDAY,
            person_name="Alex",
        )
    )


@pytest.mark.asyncio
async def test_personal_calendar_recommendation_loads_database_calendar_and_maps_source(
    personal_calendar_repository,
    customer_account_id,
) -> None:
    event = await _add_birthday(personal_calendar_repository, customer_account_id)
    provider = MatchingDealInventoryProvider()
    use_case = RecommendPersonalCalendarDeals(
        repository=personal_calendar_repository,
        inventory_provider=provider,
    )

    result = await use_case(
        RecommendPersonalCalendarDealsQuery(
            account_id=customer_account_id,
            origin_city="Edinburgh",
            origin_country="United Kingdom",
            reference_date=date(2026, 7, 20),
            pricing_currency="GBP",
            calendar_item_id=event.id,
            calendar_item_type=CalendarSourceType.EVENT,
            plan_types=(PlanType.HOTEL,),
            tiers=(DealTier.LITE,),
            target_budget=Decimal("1000"),
            maximum_budget=Decimal("1500"),
        )
    )

    assert result.account_id == str(customer_account_id)
    assert len(result.opportunities) == 1
    assert result.opportunities[0].source_item_id == str(event.id)
    assert result.opportunities[0].source_label == "Alex's Birthday"
    assert provider.requests
    assert all(request.source_item_id == str(event.id) for request in provider.requests)
    assert all(
        request.holiday_types == (HolidayTypeEnum.WELLNESS_AND_SPA_RETREATS,)
        for request in provider.requests
    )
    assert any(
        option.status is RecommendationStatus.AVAILABLE
        for window in result.opportunities[0].windows
        for option in window.options
    )


@pytest.mark.asyncio
async def test_personal_calendar_recommendation_rejects_unknown_selected_item(
    personal_calendar_repository,
    customer_account_id,
) -> None:
    await _add_birthday(personal_calendar_repository, customer_account_id)
    use_case = RecommendPersonalCalendarDeals(
        repository=personal_calendar_repository,
        inventory_provider=MatchingDealInventoryProvider(),
    )

    with pytest.raises(PersonalCalendarRecommendationItemNotFoundError):
        await use_case(
            RecommendPersonalCalendarDealsQuery(
                account_id=customer_account_id,
                origin_city="Edinburgh",
                origin_country="United Kingdom",
                reference_date=date(2026, 7, 20),
                pricing_currency="GBP",
                calendar_item_id=uuid7(),
                calendar_item_type=CalendarSourceType.EVENT,
                plan_types=(PlanType.HOTEL,),
                tiers=(DealTier.LITE,),
            )
        )


def test_personal_calendar_recommendation_http_route(
    personal_calendar_repository,
    customer_account_id,
) -> None:
    import asyncio

    event = asyncio.run(_add_birthday(personal_calendar_repository, customer_account_id))
    provider = MatchingDealInventoryProvider()
    app = FastAPI()
    app.include_router(customer_personal_calendar_router, prefix="/v1")
    app.dependency_overrides[build_recommend_personal_calendar_deals] = lambda: (
        RecommendPersonalCalendarDeals(
            repository=personal_calendar_repository,
            inventory_provider=provider,
        )
    )
    client = TestClient(app)

    response = client.post(
        f"/v1/personal-calendar/{customer_account_id}/recommendations",
        json={
            "originCity": "Edinburgh",
            "originCountry": "United Kingdom",
            "referenceDate": "2026-07-20",
            "pricingCurrency": "GBP",
            "calendarItemId": str(event.id),
            "calendarItemType": "event",
            "planTypes": ["hotel"],
            "tiers": ["Lite"],
            "targetBudget": "1000",
            "maximumBudget": "1500",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["output"]["accountId"] == str(customer_account_id)
    assert payload["output"]["opportunities"][0]["sourceItemId"] == str(event.id)
    options = payload["output"]["opportunities"][0]["windows"][0]["options"]
    assert options[0]["status"] == "available"


def test_personal_calendar_integration_preserves_bucket_list_recommendation_route() -> None:
    from luxtj.contexts.customer.presentation.http.router import customer_bucket_list_router

    app = FastAPI()
    app.include_router(customer_bucket_list_router, prefix="/v1")
    app.include_router(customer_personal_calendar_router, prefix="/v1")
    paths = app.openapi()["paths"]

    assert "post" in paths["/v1/bucket-list/{account_id}/recommendations"]
    assert "post" in paths["/v1/personal-calendar/{account_id}/recommendations"]


def test_recommendation_engine_reuses_personal_calendar_domain_entities() -> None:
    from luxtj.contexts.customer.application.personal_calendar_recommendation_engine import (
        enums as recommendation_enums,
    )
    from luxtj.contexts.customer.application.personal_calendar_recommendation_engine import (
        models as recommendation_models,
    )

    for redundant_name in (
        "CalendarEventType",
        "BirthdayFor",
        "AnniversaryFor",
        "HolidayType",
    ):
        assert not hasattr(recommendation_enums, redundant_name)

    assert not hasattr(recommendation_models, "CalendarEventInput")
    assert not hasattr(recommendation_models, "CalendarPeriodInput")


async def test_pending_inventory_provider_returns_structured_unavailable_result(
    personal_calendar_repository,
    customer_account_id,
) -> None:
    from luxtj.contexts.customer.infrastructure.personal_calendar_recommendations.deal_inventory_provider import (
        PendingPersonalCalendarDealInventoryProvider,
    )

    await _add_birthday(personal_calendar_repository, customer_account_id)
    use_case = RecommendPersonalCalendarDeals(
        repository=personal_calendar_repository,
        inventory_provider=PendingPersonalCalendarDealInventoryProvider(),
    )

    result = await use_case(
        RecommendPersonalCalendarDealsQuery(
            account_id=customer_account_id,
            origin_city="Edinburgh",
            origin_country="United Kingdom",
            reference_date=date(2026, 7, 20),
            pricing_currency="GBP",
            plan_types=(PlanType.HOTEL,),
            tiers=(DealTier.LITE,),
        )
    )

    options = [
        option
        for opportunity in result.opportunities
        for window in opportunity.windows
        for option in window.options
    ]
    assert options
    assert all(option.status is RecommendationStatus.UNAVAILABLE for option in options)
    assert all(
        "provider_error" in {reason.value for reason in option.reason_codes} for option in options
    )
