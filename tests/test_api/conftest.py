from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.main import api_application_lifespan, server_factory


@pytest.fixture
async def app_server() -> AsyncIterator[FastAPI]:
    _app = server_factory()
    async with api_application_lifespan(_app):
        yield _app


@pytest.fixture
async def client(app_server: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app_server), base_url="http://test") as ac:
        yield ac
