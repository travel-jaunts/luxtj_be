"""Flight blender — orchestration (City Travel provider registered; methods filled later)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.flight.domain.provider import FlightProvider
from luxtj.contexts.flight.infrastructure.citytravel.provider import CityTravelFlightProvider
from luxtj.contexts.flight.infrastructure.persistence.sqlalchemy_models import FlightSearchRow
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.infrastructure.http import MultiHttpClient
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)

_SEARCH_DONE = object()


class FlightBlender:
    def __init__(
        self,
        session: AsyncSession,
        *,
        http_client: Any | None = None,
        multi_http: MultiHttpClient | None = None,
    ) -> None:
        self._session = session
        self._http = http_client
        self._curl = multi_http or MultiHttpClient(http_client, session=session)

    async def create_search_session(
        self, search_data: dict[str, Any], user_id: str | None = None
    ) -> FlightSearchRow:
        now = timeutils.datetime_now()
        row = FlightSearchRow(
            id=str(uuid.uuid4()),
            user_id=user_id,
            trip_type=str(search_data.get("trip_type") or "oneway"),
            cabin_class=str(search_data.get("cabin_class") or "Economy"),
            adult_count=int(search_data.get("adult_config") or 1),
            child_count=int(search_data.get("child_config") or 0),
            infant_count=int(search_data.get("infant_config") or 0),
            search_data=search_data,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_search_session(self, search_id: str) -> FlightSearchRow | None:
        return await self._session.get(FlightSearchRow, search_id)

    def _get_active_flight_booking_sources(self) -> list[dict[str, Any]]:
        registry = get_integration_registry()
        flight_sub = registry.active_sub_modules.get("FLIGHT")
        if flight_sub is None:
            return []
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()
        for key, api in list(registry.active_booking_apis.items()):
            if ":" in key:
                continue
            if api.sub_module_id != flight_sub.id:
                continue
            if api.code in seen:
                continue
            seen.add(api.code)
            sources.append(
                {
                    "code": api.code,
                    "name": api.name,
                    "configuration": api.runtime_configuration(),
                    "id": str(api.id),
                }
            )
        return sources

    def resolve_provider(
        self,
        code: str,
        config: dict[str, Any] | None = None,
        api_id: str | None = None,
    ) -> FlightProvider | None:
        if code.lower() == "citytravel":
            return CityTravelFlightProvider(
                config or {},
                api_id,
                session=self._session,
                http_client=self._http,
            )
        logger.debug("No flight provider registered for code=%s", code)
        return None

    def resolve_provider_by_source(self, source: str) -> FlightProvider | None:
        registry = get_integration_registry()
        api = registry.resolve_booking_api(source, sub_module="FLIGHT") or registry.resolve_booking_api(
            source
        )
        if api is None:
            return None
        return self.resolve_provider(source, api.runtime_configuration(), str(api.id))

    def resolve_provider_from_token(self, result_token: str) -> FlightProvider | None:
        decoded = FlightCommon.decode_result_token(result_token)
        if not decoded:
            return None
        return self.resolve_provider_by_source(str(decoded["booking_source"]))

    async def search(self, search_id: str) -> AsyncIterator[dict[str, Any]]:
        session = await self.get_search_session(search_id)
        if not session:
            yield {"status": False, "message": "Invalid search session"}
            return

        raw_search = session.search_data if isinstance(session.search_data, dict) else {}
        search_data = {
            **raw_search,
            "search_id": search_id,
        }

        sources = self._get_active_flight_booking_sources()
        if not sources:
            yield {"status": False, "message": "No active flight booking sources"}
            return

        handle_map: dict[str, Any] = {}
        provider_by_code: dict[str, FlightProvider] = {}
        search_by_code: dict[str, dict[str, Any]] = {}

        for source in sources:
            code = str(source["code"])
            provider = self.resolve_provider(code, source["configuration"], source["id"])
            if provider is None:
                continue
            credentials_ready = getattr(provider, "credentials_ready", None)
            if callable(credentials_ready) and not credentials_ready():
                logger.warning(
                    "Skipping flight source %s: credentials missing in Integrations booking API config",
                    code,
                )
                continue
            search_for_provider = {
                **search_data,
                "booking_api_id": source["id"],
                "booking_source_code": code,
            }
            handles = provider.get_search_request(search_for_provider)
            if not handles:
                continue
            provider_by_code[code] = provider
            search_by_code[code] = search_for_provider
            handle_map[code] = handles

        if not handle_map:
            yield {
                "status": True,
                "message": "Completed",
                "data": {"flights": [], "moreResults": False},
                "errors": None,
            }
            return

        raw_q: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
        out_q: asyncio.Queue[dict[str, Any] | object] = asyncio.Queue()

        async def _on_response(provider_code: str, raw: str) -> None:
            await raw_q.put((provider_code, raw))

        async def _run_http() -> None:
            try:
                await self._curl.stream_execute(handle_map, _on_response)
            except Exception:
                logger.exception("Flight search multi-HTTP failed search_id=%s", search_id)
            finally:
                await raw_q.put(None)

        async def _process_raw() -> None:
            try:
                while True:
                    item = await raw_q.get()
                    if item is None:
                        break
                    provider_code, raw = item
                    provider = provider_by_code.get(provider_code)
                    search_for_provider = search_by_code.get(provider_code) or search_data
                    if provider is None:
                        continue
                    formatted = await provider.format_search_response(raw, search_for_provider)
                    flights = formatted.get("data") if isinstance(formatted, dict) else None
                    if not isinstance(flights, list) or not flights:
                        continue
                    await out_q.put(
                        {
                            "status": True,
                            "message": "Inprogress",
                            "data": {"flights": flights, "moreResults": True},
                            "errors": None,
                        }
                    )
            except Exception:
                logger.exception("Flight search format failed search_id=%s", search_id)
            finally:
                await out_q.put(_SEARCH_DONE)

        http_task = asyncio.create_task(_run_http())
        proc_task = asyncio.create_task(_process_raw())
        try:
            while True:
                chunk = await out_q.get()
                if chunk is _SEARCH_DONE:
                    break
                if isinstance(chunk, dict):
                    yield chunk
        finally:
            await asyncio.gather(http_task, proc_task, return_exceptions=True)

        yield {
            "status": True,
            "message": "Completed",
            "data": {"flights": [], "moreResults": False},
            "errors": None,
        }

    async def get_upsell(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider not available"}
        decoded = FlightCommon.decode_result_token(result_token)
        assert decoded is not None
        return await provider.get_upsell(str(decoded["token"]))

    async def get_update_fare_quote(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider not available"}
        decoded = FlightCommon.decode_result_token(result_token)
        assert decoded is not None
        return await provider.get_update_fare_quote(str(decoded["token"]))

    async def get_extra_services(self, result_token: str) -> dict[str, Any]:
        provider = self.resolve_provider_from_token(result_token)
        if not provider:
            return {"status": False, "message": "Invalid token or provider not available"}
        decoded = FlightCommon.decode_result_token(result_token)
        assert decoded is not None
        return await provider.get_extra_services(str(decoded["token"]))

    async def not_implemented(self, action: str) -> dict[str, Any]:
        return {"status": False, "message": f"{action} is not implemented yet"}
