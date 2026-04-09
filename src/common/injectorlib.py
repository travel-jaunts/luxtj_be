from fastapi import FastAPI, Request
from httpx import AsyncClient

from common.kernellib import get_http_client


def fastapi_app_handle(request: Request) -> FastAPI:
    return request.app


def http_client_handle(request: Request) -> AsyncClient:
    return get_http_client(fastapi_app_handle(request))
