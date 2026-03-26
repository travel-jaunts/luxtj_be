from fastapi import FastAPI, Request


def fastapi_app_handle(request: Request) -> FastAPI:
    return request.app
