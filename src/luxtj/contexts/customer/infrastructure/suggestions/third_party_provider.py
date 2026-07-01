from httpx import AsyncClient

from luxtj.contexts.customer.application.ports import (
    DestinationSuggestion,
    DestinationSuggestionResult,
)
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum


class ThirdPartyDestinationSuggestionProvider:
    def __init__(
        self,
        http_client: AsyncClient,
        *,
        base_url: str,
        api_key: str | None,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def suggest(
        self,
        *,
        query: str,
        selected_kind: BucketDestinationKindEnum,
        selected_name: str | None,
    ) -> DestinationSuggestionResult:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        response = await self._http_client.post(
            f"{self._base_url}/bucket-list/suggestions",
            json={
                "query": query,
                "selectedKind": selected_kind.value,
                "selectedName": selected_name,
            },
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()

        selected_payload = payload["selected"]
        alternatives_payload = payload.get("alternatives", [])

        return DestinationSuggestionResult(
            selected=_to_suggestion(selected_payload),
            alternatives=[_to_suggestion(item) for item in alternatives_payload],
        )


def _to_suggestion(payload: dict[str, object]) -> DestinationSuggestion:
    return DestinationSuggestion(
        destination_kind=BucketDestinationKindEnum(str(payload["destinationKind"])),
        destination_name=str(payload["destinationName"]),
        parent_country=str(payload["parentCountry"]) if payload.get("parentCountry") else None,
        ideal_days=int(payload["idealDays"]),
    )
