from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.http.async_http_client import AsyncTwilioHttpClient

from luxtj.shared_kernel.infrastructure.events.in_process import InProcessEventPublisher
from luxtj.shared_kernel.infrastructure.events.outbox import OutboxEventPublisher
from luxtj.shared_kernel.infrastructure.persistence.sqlalchemy import (
    AsyncSessionFactory,
    session_scope,
)


def fastapi_app_handle(request: Request) -> FastAPI:
    return request.app


def http_client_handle(request: Request) -> AsyncClient:
    return request.app.state.http_client


def domain_event_publisher_handle(request: Request) -> InProcessEventPublisher:
    return request.app.state.domain_event_publisher


def database_session_factory_handle(request: Request) -> AsyncSessionFactory:
    return request.app.state.database_session_factory


async def database_session_handle(request: Request) -> AsyncIterator[AsyncSession]:
    async with session_scope(request.app.state.database_session_factory) as session:
        yield session


def outbox_event_publisher_handle(session: AsyncSession) -> OutboxEventPublisher:
    return OutboxEventPublisher(session)


def twilio_client_handle(request: Request) -> AsyncTwilioHttpClient:
    return request.app.state.twilio_http_client
