from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from common.kernellib import (
    get_database_session_factory,
    get_domain_event_publisher,
    get_http_client,
)
from luxtj.shared_kernel.infrastructure.events import InProcessEventPublisher
from luxtj.shared_kernel.infrastructure.persistence import AsyncSessionFactory, session_scope


def fastapi_app_handle(request: Request) -> FastAPI:
    return request.app


def http_client_handle(request: Request) -> AsyncClient:
    return get_http_client(fastapi_app_handle(request))


def domain_event_publisher_handle(request: Request) -> InProcessEventPublisher:
    return get_domain_event_publisher(fastapi_app_handle(request))


def database_session_factory_handle(request: Request) -> AsyncSessionFactory:
    return get_database_session_factory(fastapi_app_handle(request))


async def database_session_handle(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = database_session_factory_handle(request)
    async with session_scope(session_factory) as session:
        yield session
