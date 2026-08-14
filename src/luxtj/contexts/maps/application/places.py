"""Google Places proxy — credentials from admin Integrations `googlemap` other_api."""

from __future__ import annotations

from typing import Any

import httpx

from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle

logger = get_logger_handle(__name__)

GOOGLEMAP_CODE = "googlemap"
PLACES_AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class MapsConfigError(Exception):
    """Google Maps other_api inactive or API Key missing."""


def _google_maps_api_key() -> str:
    other = get_integration_registry().resolve_other_api(GOOGLEMAP_CODE)
    if other is None:
        raise MapsConfigError(
            "Google Maps is not enabled. Activate it under Admin → Integrations → Other APIs."
        )
    key = credential_value(other.credential_configs(), "API Key")
    if not key:
        raise MapsConfigError(
            "Google Maps API Key is missing. Set it under Admin → Integrations → Google Maps."
        )
    return key


async def places_autocomplete(
    *,
    input_text: str,
    session_token: str | None = None,
    language: str | None = None,
    components: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Proxy Google Place Autocomplete (cities). Key never leaves the backend."""
    query = (input_text or "").strip()
    if len(query) < 2:
        return []

    params: dict[str, str] = {
        "input": query,
        "types": "(cities)",
        "key": _google_maps_api_key(),
    }
    if session_token:
        params["sessiontoken"] = session_token
    if language:
        params["language"] = language
    if components:
        params["components"] = components

    owns = http_client is None
    client = http_client or httpx.AsyncClient(timeout=15.0)
    try:
        resp = await client.get(PLACES_AUTOCOMPLETE_URL, params=params)
        data = resp.json()
    except Exception as exc:
        logger.warning("Google Places autocomplete failed: %s", exc)
        raise RuntimeError("Google Places autocomplete request failed") from exc
    finally:
        if owns:
            await client.aclose()

    status = str(data.get("status") or "")
    if status not in ("OK", "ZERO_RESULTS"):
        err = data.get("error_message") or status or "Unknown Google Places error"
        logger.warning("Google Places autocomplete status=%s err=%s", status, err)
        raise RuntimeError(f"Google Places autocomplete error: {err}")

    predictions = data.get("predictions") or []
    out: list[dict[str, Any]] = []
    for p in predictions:
        if not isinstance(p, dict):
            continue
        place_id = str(p.get("place_id") or "").strip()
        if not place_id:
            continue
        structured = (
            p.get("structured_formatting")
            if isinstance(p.get("structured_formatting"), dict)
            else {}
        )
        out.append(
            {
                "placeId": place_id,
                "description": str(p.get("description") or ""),
                "mainText": str(structured.get("main_text") or p.get("description") or ""),
                "secondaryText": str(structured.get("secondary_text") or ""),
                "types": [str(t) for t in (p.get("types") or []) if t],
            }
        )
    return out


async def place_details(
    *,
    place_id: str,
    session_token: str | None = None,
    language: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Proxy Google Place Details (name, address, lat/lng)."""
    pid = (place_id or "").strip()
    if not pid:
        raise ValueError("placeId is required")

    params: dict[str, str] = {
        "place_id": pid,
        "fields": "place_id,name,formatted_address,geometry,address_component,types",
        "key": _google_maps_api_key(),
    }
    if session_token:
        params["sessiontoken"] = session_token
    if language:
        params["language"] = language

    owns = http_client is None
    client = http_client or httpx.AsyncClient(timeout=15.0)
    try:
        resp = await client.get(PLACES_DETAILS_URL, params=params)
        data = resp.json()
    except Exception as exc:
        logger.warning("Google Places details failed: %s", exc)
        raise RuntimeError("Google Places details request failed") from exc
    finally:
        if owns:
            await client.aclose()

    status = str(data.get("status") or "")
    if status != "OK":
        err = data.get("error_message") or status or "Unknown Google Places error"
        logger.warning("Google Places details status=%s err=%s", status, err)
        raise RuntimeError(f"Google Places details error: {err}")

    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    geometry = result.get("geometry") if isinstance(result.get("geometry"), dict) else {}
    location = geometry.get("location") if isinstance(geometry.get("location"), dict) else {}
    lat = location.get("lat")
    lng = location.get("lng")

    country_code = ""
    country_name = ""
    locality = ""
    admin_area = ""
    for comp in result.get("address_components") or []:
        if not isinstance(comp, dict):
            continue
        types = [str(t) for t in (comp.get("types") or [])]
        if "country" in types:
            country_code = str(comp.get("short_name") or "").upper()
            country_name = str(comp.get("long_name") or "")
        if "locality" in types or "postal_town" in types:
            locality = str(comp.get("long_name") or "")
        if "administrative_area_level_1" in types:
            admin_area = str(comp.get("long_name") or "")

    return {
        "placeId": str(result.get("place_id") or pid),
        "name": str(result.get("name") or ""),
        "formattedAddress": str(result.get("formatted_address") or ""),
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
        "countryCode": country_code or None,
        "countryName": country_name or None,
        "locality": locality or None,
        "adminArea": admin_area or None,
        "types": [str(t) for t in (result.get("types") or []) if t],
    }
