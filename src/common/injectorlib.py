from fastapi import FastAPI, Request
from niquests import Session

from common.kernellib import get_http_client


def fastapi_app_handle(request: Request) -> FastAPI:
    return request.app


def http_client_handle(request: Request) -> Session:
    return get_http_client(fastapi_app_handle(request))
