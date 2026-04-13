from httpx import AsyncClient


async def test_ping(client: AsyncClient) -> None:
    resp = await client.post("/ping")
    assert resp.status_code == 200
    assert resp.json() == "pong"


async def test_health(client: AsyncClient) -> None:
    resp = await client.post("/health")
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "output": {"uptimeSeconds": 0, "databaseConnected": False},
    }
