from asyncio import Lock as CoroutineLock
from base64 import b64encode
from typing import ParamSpec, TypeVar

from httpx import AsyncClient, HTTPStatusError, Response

from app.core.bases import IAsyncCachingProvider, SingletonMeta
from app.core.config import get_settings
from app.core.logging import get_logger

P = ParamSpec("P")
R = TypeVar("R")

settings = get_settings()
logger = get_logger(__name__)


async def fetch_access_token(http_client: AsyncClient, scopes: list[str]) -> str:
    """makes the api call to tourradar to fetch the access token for authentication"""
    _invalid_token_placeholder: str = ""

    _req_body = {
        "grant_type": "client_credentials",
    }
    if len(scopes) > 0:
        _req_body.update(
            {"scope": " ".join(scopes)}
        )  # scopes are space-separated in the request body

    try:
        tourradar_oauth_response: Response = await http_client.post(
            url=settings.app_tourradar_oauth_base_url + "/oauth2/token",
            headers={
                "Authorization": "Basic "
                + b64encode(
                    f"{settings.app_tourradar_oauth_client_id}:{settings.app_tourradar_oauth_client_secret}".encode()
                ).decode(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=_req_body,
            timeout=10.0,
        )

    except HTTPStatusError as e:
        logger.error(
            "HTTP error while fetching access token from TourRadar OAuth API | error=%s",
            str(e),
        )
        raise

    else:
        _resp_body = tourradar_oauth_response.json()

    if tourradar_oauth_response.status_code != 200:
        logger.error(
            "Failed to fetch access token from TourRadar OAuth API | status_code=%s response=%s",
            tourradar_oauth_response.status_code,
            _resp_body,
        )
        # biz errors here, rising from config issues or request malformation
        return _invalid_token_placeholder

    else:
        import pprint as pp

        pp.pprint(_resp_body)
        return _resp_body.get("access_token", _invalid_token_placeholder)


class TourradarApiAccessManager(metaclass=SingletonMeta):
    def __init__(self, cache_client: IAsyncCachingProvider, http_client: AsyncClient) -> None:
        self._cache_client = cache_client
        self._http_client = http_client

        self._login_lock: CoroutineLock = CoroutineLock()
        return

    @classmethod
    def _cache_key(cls) -> str:
        return "tourradar_api_access_token"

    async def get_access_token(self, scopes: list[str]) -> str:
        """Returns a valid access token, either from cache or by making a new request if not present/expired"""
        _cached_token: str | None = await self._cache_client.get(self._cache_key())
        if _cached_token:
            return _cached_token

        # acquire lock to ensure only one coroutine makes the token fetch request when cache is missed
        async with self._login_lock:
            # double-check cache after acquiring lock to prevent redundant requests in high concurrency scenarios
            _cached_token = await self._cache_client.get(self._cache_key())
            if _cached_token:
                return _cached_token

            # fetch new token and cache it
            _new_token: str = await fetch_access_token(self._http_client, scopes)
            if _new_token:
                # caching the token with a TTL of 3500 seconds (assuming token validity of 3600 seconds) to account for clock skew and ensure timely refresh
                await self._cache_client.set(self._cache_key(), _new_token, ttl_seconds=3500)
                return _new_token

            # in case of failure to fetch a valid token, return empty string (or could raise an exception based on design choice)
            return ""


class TourradarApiCaller:
    def __init__(self, access_manager: TourradarApiAccessManager, http_client: AsyncClient) -> None:
        self._api_access_manager: TourradarApiAccessManager = access_manager
        self._http_client: AsyncClient = http_client
        return

    # TAXONOMY ------------------------------------------------------------------------------------
    async def get_currencies(self):
        _taxonomy_currency_response: Response = await self._http_client.get(
            url=settings.app_tourradar_api_base_url + "/v1/taxonomy/currencies",
            headers={
                "Authorization": "Bearer " + await self._api_access_manager.get_access_token([])
            },
        )
        return _taxonomy_currency_response.json()
