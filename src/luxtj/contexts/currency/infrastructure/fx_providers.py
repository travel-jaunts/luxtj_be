"""FX rate providers — ExchangeRate-API from integration registry, stub fallback."""

from __future__ import annotations

from typing import Any

import httpx

from luxtj.contexts.currency.infrastructure.stub_rate_provider import StubFxRateProvider
from luxtj.contexts.integration.domain.catalog import credential_value
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle

logger = get_logger_handle(__name__)

EXCHANGERATE_API_CODE = "exchangerate-api"
EXCHANGERATE_API_BASE_URL = "https://v6.exchangerate-api.com/v6"


class ExchangeRateApiFxRateProvider:
    """Live rates via ExchangeRate-API v6 Standard endpoint.

    Credentials come from `other_apis` code `exchangerate-api` (admin registry).
    GET https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{BASE}
    """

    def __init__(
        self,
        *,
        base_url: str = EXCHANGERATE_API_BASE_URL,
        http_client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = http_client
        self._timeout = timeout

    def _api_key(self) -> str:
        other = get_integration_registry().resolve_other_api(EXCHANGERATE_API_CODE)
        if other is None:
            return ""
        return credential_value(other.credential_configs(), "API Key")

    def fetch_rates(self, pairs: list[tuple[str, str]]) -> list[dict[str, str | float | None]]:
        results: list[dict[str, str | float | None]] = []
        api_key = self._api_key()
        if not api_key:
            logger.warning(
                "ExchangeRate-API inactive or API Key missing in integration registry "
                "(other_apis/%s)",
                EXCHANGERATE_API_CODE,
            )
            for frm, to in pairs:
                results.append({"from": frm.upper(), "to": to.upper(), "rate": None})
            return results

        by_from: dict[str, list[str]] = {}
        for frm, to in pairs:
            by_from.setdefault(frm.upper(), []).append(to.upper())

        owned = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout, follow_redirects=True)
        try:
            rate_map: dict[tuple[str, str], float | None] = {}
            for frm, tos in by_from.items():
                unique_tos = sorted({t for t in tos if t != frm})
                for to in tos:
                    if to == frm:
                        rate_map[(frm, to)] = 1.0
                if not unique_tos:
                    continue
                try:
                    resp = client.get(f"{self._base_url}/{api_key}/latest/{frm}")
                    resp.raise_for_status()
                    payload: dict[str, Any] = resp.json()
                    if str(payload.get("result") or "").lower() != "success":
                        error_type = payload.get("error-type") or "unknown"
                        raise RuntimeError(f"ExchangeRate-API error: {error_type}")
                    rates = payload.get("conversion_rates") or {}
                    for to in unique_tos:
                        val = rates.get(to)
                        rate_map[(frm, to)] = float(val) if val is not None else None
                except Exception as exc:
                    logger.warning("ExchangeRate-API FX fetch failed from=%s err=%s", frm, exc)
                    for to in unique_tos:
                        rate_map.setdefault((frm, to), None)
            for frm, to in pairs:
                results.append(
                    {
                        "from": frm.upper(),
                        "to": to.upper(),
                        "rate": rate_map.get((frm.upper(), to.upper())),
                    }
                )
        finally:
            if owned:
                client.close()
        return results


class CompositeFxRateProvider:
    """Try providers in order; first non-null rate wins per pair."""

    def __init__(self, providers: list[Any]) -> None:
        self._providers = providers

    def fetch_rates(self, pairs: list[tuple[str, str]]) -> list[dict[str, str | float | None]]:
        if not pairs:
            return []
        pending = list(pairs)
        resolved: dict[tuple[str, str], float | None] = {}
        for provider in self._providers:
            if not pending:
                break
            fetched = provider.fetch_rates(pending)
            still: list[tuple[str, str]] = []
            for item in fetched:
                frm = str(item.get("from") or "")
                to = str(item.get("to") or "")
                rate = item.get("rate")
                if isinstance(rate, (int, float)) and float(rate) > 0:
                    resolved[(frm, to)] = float(rate)
                else:
                    still.append((frm, to))
            pending = still
        for frm, to in pending:
            resolved.setdefault((frm.upper(), to.upper()), None)
        return [
            {
                "from": frm.upper(),
                "to": to.upper(),
                "rate": resolved.get((frm.upper(), to.upper())),
            }
            for frm, to in pairs
        ]


def build_default_fx_rate_provider() -> Any:
    return CompositeFxRateProvider(
        [
            ExchangeRateApiFxRateProvider(),
            StubFxRateProvider(),
        ]
    )
