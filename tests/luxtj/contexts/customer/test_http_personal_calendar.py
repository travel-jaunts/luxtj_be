from fastapi import FastAPI
from fastapi.testclient import TestClient

from luxtj.contexts.customer.application.use_cases import (
    AddPersonalCalendarEvent,
    AddPersonalCalendarPeriod,
    GetPersonalCalendarConsolidatedView,
    GetPersonalCalendarHolidayTypes,
)
from luxtj.contexts.customer.bootstrap import (
    build_add_personal_calendar_event,
    build_add_personal_calendar_period,
    build_get_personal_calendar_consolidated_view,
    build_get_personal_calendar_holiday_types,
)
from luxtj.contexts.customer.presentation.http.router import customer_personal_calendar_router


def _create_client(personal_calendar_repository) -> TestClient:
    app = FastAPI()
    app.include_router(customer_personal_calendar_router, prefix="/v1")

    app.dependency_overrides[build_add_personal_calendar_event] = lambda: AddPersonalCalendarEvent(
        repository=personal_calendar_repository
    )
    app.dependency_overrides[build_add_personal_calendar_period] = lambda: (
        AddPersonalCalendarPeriod(repository=personal_calendar_repository)
    )
    app.dependency_overrides[build_get_personal_calendar_holiday_types] = lambda: (
        GetPersonalCalendarHolidayTypes()
    )
    app.dependency_overrides[build_get_personal_calendar_consolidated_view] = lambda: (
        GetPersonalCalendarConsolidatedView(repository=personal_calendar_repository)
    )

    return TestClient(app)


def test_personal_calendar_http_create_and_holiday_types(
    personal_calendar_repository, customer_account_id
) -> None:
    client = _create_client(personal_calendar_repository)
    account_id = str(customer_account_id)

    event_response = client.post(
        f"/v1/personal-calendar/{account_id}/events/add",
        json={
            "eventType": "birthday",
            "birthdayFor": "my_birthday",
            "personName": "Me",
            "eventDate": "2026-08-10",
            "holidayTypes": ["Signature Experiences"],
        },
    )
    assert event_response.status_code == 200
    assert event_response.json()["output"]["eventType"] == "birthday"

    period_response = client.post(
        f"/v1/personal-calendar/{account_id}/periods/add",
        json={
            "periodName": "Year End",
            "periodStart": "2026-12-20",
            "periodEnd": "2026-12-31",
            "isDateFlexible": False,
            "holidayTypes": ["Family Luxury Holidays"],
        },
    )
    assert period_response.status_code == 200
    assert period_response.json()["output"]["periodName"] == "Year End"

    holiday_types_response = client.post("/v1/personal-calendar/holiday-types/view", json={})
    assert holiday_types_response.status_code == 200
    assert "Signature Experiences" in holiday_types_response.json()["output"]["holidayTypes"]

    consolidated_view_response = client.post(f"/v1/personal-calendar/{account_id}/view", json={})
    assert consolidated_view_response.status_code == 200
    items = consolidated_view_response.json()["output"]["items"]
    assert len(items) == 2
    assert {item["itemType"] for item in items} == {"event", "period"}


def test_personal_calendar_http_rejects_invalid_holiday_types(
    personal_calendar_repository, customer_account_id
) -> None:
    client = _create_client(personal_calendar_repository)
    account_id = str(customer_account_id)

    response = client.post(
        f"/v1/personal-calendar/{account_id}/events/add",
        json={
            "eventType": "special_occasion",
            "eventName": "Promotion",
            "eventDate": "2026-08-10",
            "holidayTypes": ["Invalid Holiday Type"],
        },
    )
    assert response.status_code == 422
