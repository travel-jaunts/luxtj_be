import pytest
from fastapi.testclient import TestClient

from luxtj.bootstrap.api import server_factory


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(server_factory())
