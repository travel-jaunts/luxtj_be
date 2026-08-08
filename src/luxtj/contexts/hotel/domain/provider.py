"""Hotel provider SPI — mirrors TeenvaHotelProviderInterface."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from luxtj.shared_kernel.infrastructure.http import HandleDescriptor


@runtime_checkable
class HotelProvider(Protocol):
    """Contract for hotel booking source providers (e.g. RateHawk)."""

    booking_source: str
    booking_api_id: str | None

    def get_search_request(self, search_data: dict[str, Any]) -> list[HandleDescriptor]:
        """Build HTTP handle descriptor(s) for a hotel search."""
        ...

    async def format_search_response(
        self,
        raw_response: Any,
        search_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Format raw search response to normalized hotel list."""
        ...

    async def get_hotel_details(self, result_token: str) -> dict[str, Any]: ...

    async def get_room_list(self, result_token: str) -> dict[str, Any]: ...

    async def block_room(
        self, result_token: str, passengers: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]: ...

    async def pre_book(self, list_token: str) -> dict[str, Any]: ...

    async def process_booking(self, request: dict[str, Any]) -> dict[str, Any]: ...

    async def get_booking_details(self, booking_reference: str) -> dict[str, Any]: ...

    async def cancel_booking(self, booking_reference: str) -> dict[str, Any]: ...
