"""Flight provider SPI — mirrors TeenvaFlightProviderInterface."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from luxtj.shared_kernel.infrastructure.http import HandleDescriptor


@runtime_checkable
class FlightProvider(Protocol):
    """Contract for flight booking source providers (e.g. City Travel)."""

    booking_source: str
    booking_api_id: str | None

    def get_search_request(self, search_data: dict[str, Any]) -> list[HandleDescriptor]:
        """Build HTTP handle descriptor(s) for a flight search."""
        ...

    async def format_search_response(
        self,
        raw_response: Any,
        search_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Format raw search response to normalized flight list (admin currency)."""
        ...

    async def get_upsell(self, token: str) -> dict[str, Any]: ...

    async def get_update_fare_quote(self, token: str) -> dict[str, Any]: ...

    async def get_extra_services(self, token: str) -> dict[str, Any]: ...

    async def get_flight_row_from_token_for_pricing(self, token: str) -> dict[str, Any]: ...

    async def get_pre_book_data(
        self,
        token: str,
        app_reference: str,
        passengers: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    async def hold_ticket(self, request: dict[str, Any]) -> dict[str, Any]: ...

    async def issue_ticket(self, locator: str) -> dict[str, Any]: ...

    async def refresh_booking_from_supplier(
        self, locator: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    async def cancel_booking(
        self, locator: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
