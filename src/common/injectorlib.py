from fastapi import FastAPI, Request
from httpx import AsyncClient

from common.kernellib import get_domain_event_publisher, get_http_client
from luxtj.application.service.event import InProcessEventPublisher


def fastapi_app_handle(request: Request) -> FastAPI:
    return request.app


def http_client_handle(request: Request) -> AsyncClient:
    return get_http_client(fastapi_app_handle(request))


def domain_event_publisher_handle(request: Request) -> InProcessEventPublisher:
    return get_domain_event_publisher(fastapi_app_handle(request))
