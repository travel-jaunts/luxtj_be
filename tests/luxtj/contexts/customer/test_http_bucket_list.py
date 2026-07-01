from fastapi import FastAPI
from fastapi.testclient import TestClient

from luxtj.contexts.customer.application.use_cases import (
    AddBucketListItem,
    DeleteBucketListItem,
    GetBucketList,
    SuggestDestinations,
    UpdateBucketListItem,
)
from luxtj.contexts.customer.bootstrap import (
    build_add_bucket_list_item,
    build_delete_bucket_list_item,
    build_get_bucket_list,
    build_suggest_destinations,
    build_update_bucket_list_item,
)
from luxtj.contexts.customer.presentation.http.router import customer_bucket_list_router


def _create_client(bucket_list_repository, suggestion_provider, event_publisher) -> TestClient:
    app = FastAPI()
    app.include_router(customer_bucket_list_router, prefix="/v1")

    app.dependency_overrides[build_add_bucket_list_item] = lambda: AddBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )
    app.dependency_overrides[build_update_bucket_list_item] = lambda: UpdateBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )
    app.dependency_overrides[build_delete_bucket_list_item] = lambda: DeleteBucketListItem(
        repository=bucket_list_repository,
        event_publisher=event_publisher,
    )
    app.dependency_overrides[build_get_bucket_list] = lambda: GetBucketList(
        repository=bucket_list_repository
    )
    app.dependency_overrides[build_suggest_destinations] = lambda: SuggestDestinations(
        provider=suggestion_provider,
        event_publisher=event_publisher,
    )

    return TestClient(app)


def test_bucket_list_http_flow(bucket_list_repository, suggestion_provider, event_publisher, customer_account_id) -> None:
    client = _create_client(bucket_list_repository, suggestion_provider, event_publisher)
    account_id = str(customer_account_id)

    suggest_response = client.post(
        f"/v1/bucket-list/{account_id}/suggestions",
        json={
            "query": "France",
            "selectedKind": "country",
            "selectedName": "France",
        },
    )
    assert suggest_response.status_code == 200
    assert suggest_response.json()["status"] == "ok"

    add_response = client.post(
        f"/v1/bucket-list/{account_id}/items/add",
        json={
            "destinationKind": "city",
            "destinationName": "Paris",
            "parentCountry": "France",
            "idealDays": 4,
            "displayOrder": 1,
        },
    )
    assert add_response.status_code == 200
    item_id = add_response.json()["output"]["id"]

    update_response = client.post(
        f"/v1/bucket-list/{account_id}/items/{item_id}/update",
        json={
            "idealDays": 5,
            "displayOrder": 2,
            "notes": "extended trip",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["output"]["idealDays"] == 5

    view_response = client.post(
        f"/v1/bucket-list/{account_id}/view",
        json={},
    )
    assert view_response.status_code == 200
    assert len(view_response.json()["output"]["items"]) == 1

    delete_response = client.post(
        f"/v1/bucket-list/{account_id}/items/{item_id}/delete",
        json={},
    )
    assert delete_response.status_code == 200

    active_view = client.post(
        f"/v1/bucket-list/{account_id}/view",
        json={"includeDeleted": False},
    )
    assert active_view.status_code == 200
    assert active_view.json()["output"]["items"] == []


def test_duplicate_destination_returns_error(
    bucket_list_repository,
    suggestion_provider,
    event_publisher,
    customer_account_id,
) -> None:
    client = _create_client(bucket_list_repository, suggestion_provider, event_publisher)
    account_id = str(customer_account_id)

    payload = {
        "destinationKind": "city",
        "destinationName": "Paris",
        "parentCountry": "France",
        "idealDays": 4,
    }
    first = client.post(f"/v1/bucket-list/{account_id}/items/add", json=payload)
    second = client.post(f"/v1/bucket-list/{account_id}/items/add", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "error"
