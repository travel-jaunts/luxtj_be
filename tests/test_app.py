import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_request_id_header(client):
    resp = client.get("/health")
    assert "x-request-id" in resp.headers


def test_items_list(client):
    resp = client.get("/api/v1/items/")
    assert resp.status_code == 200
    assert "items" in resp.json()
