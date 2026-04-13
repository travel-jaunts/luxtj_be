import pytest
from fastapi.testclient import TestClient

from api.main import server_factory


@pytest.fixture
def client():
    return TestClient(server_factory())


def test_health(client: TestClient) -> None:
    resp = client.post("/ping")
    assert resp.status_code == 200
    assert resp.json() == "pong"
