from httpx import AsyncClient

from luxtj.contexts.customer.application.ports import (
    DestinationSuggestion,
    DestinationSuggestionResult,
)
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry


class ThirdPartyDestinationSuggestionProvider:
    """Bucket-list suggestions; Base URL + API Key from other_apis registry."""

    CODE = "bucketlistsuggestions"

    def __init__(self, http_client: AsyncClient) -> None:
        self._http_client = http_client

    def _credentials(self) -> tuple[str, str | None]:
        other = get_integration_registry().resolve_other_api(self.CODE)
        if other is None:
            raise RuntimeError(
                "Bucket List Suggestions API is inactive. "
                "Activate it under Admin → Integrations → Other APIs."
            )
        configs = other.credential_configs()
        base_url = credential_value(configs, "Base URL")
        api_key = credential_value(configs, "API Key") or None
        if not base_url:
            raise RuntimeError(
                "Bucket List Suggestions Base URL is missing in integration credentials."
            )
        return base_url.rstrip("/"), api_key

    async def suggest(
        self,
        *,
        query: str,
        selected_kind: BucketDestinationKindEnum,
        selected_name: str | None,
    ) -> DestinationSuggestionResult:
        base_url, api_key = self._credentials()
        headers: dict[str, str] = {}
        if api_key:
            headers["x-api-key"] = api_key

        response = await self._http_client.post(
            f"{base_url}/bucket-list/suggestions",
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
