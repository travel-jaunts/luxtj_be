"""Public Maps / Places endpoints — key stays on the server (admin Integrations)."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import Field

from luxtj.contexts.maps.application.places import (
    MapsConfigError,
    place_details,
    places_autocomplete,
)
from luxtj.shared_kernel.presentation.http.dependencies import http_client_handle
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiSerializerBaseModel,
    ApiSuccessResponse,
)

maps_router = APIRouter(prefix="/maps", tags=["maps"])


class PlacesAutocompleteBody(ApiSerializerBaseModel):
    input: str = Field(..., min_length=1, description="User search text")
    session_token: str | None = Field(None, alias="sessionToken")
    language: str | None = None
    components: str | None = Field(
        None,
        description="Optional Google components filter, e.g. country:in",
    )


class PlaceDetailsBody(ApiSerializerBaseModel):
    place_id: str = Field(..., min_length=1, alias="placeId")
    session_token: str | None = Field(None, alias="sessionToken")
    language: str | None = None


@maps_router.post(
    "/places/autocomplete",
    response_model=ApiSuccessResponse[dict[str, Any]],
)
async def autocomplete_places(
    body: Annotated[PlacesAutocompleteBody, Body(...)],
    http_client: Annotated[httpx.AsyncClient, Depends(http_client_handle)],
) -> ApiSuccessResponse[dict[str, Any]]:
    try:
        predictions = await places_autocomplete(
            input_text=body.input,
            session_token=body.session_token,
            language=body.language,
            components=body.components,
            http_client=http_client,
        )
    except MapsConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ApiSuccessResponse(output={"predictions": predictions})


@maps_router.post(
    "/places/details",
    response_model=ApiSuccessResponse[dict[str, Any]],
)
async def get_place_details(
    body: Annotated[PlaceDetailsBody, Body(...)],
    http_client: Annotated[httpx.AsyncClient, Depends(http_client_handle)],
) -> ApiSuccessResponse[dict[str, Any]]:
    try:
        details = await place_details(
            place_id=body.place_id,
            session_token=body.session_token,
            language=body.language,
            http_client=http_client,
        )
    except MapsConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ApiSuccessResponse(output=details)
