"""Bootstrap / server-factory smoke tests."""

from fastapi.testclient import TestClient


def test_ping(client: TestClient) -> None:
    resp = client.post("/ping")
    assert resp.status_code == 200
    assert resp.json() == "pong"
