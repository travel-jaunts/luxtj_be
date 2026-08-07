from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UpdateModuleStatusCommand:
    module_id: UUID
    status: bool


@dataclass(frozen=True)
class UpdateSubModuleStatusCommand:
    sub_module_id: UUID
    status: bool


@dataclass(frozen=True)
class UpdateBookingApiCommand:
    booking_api_id: UUID
    status: bool | None = None
    api_type: str | None = None
    currency: str | None = None
    configs: dict[str, str] | None = None


@dataclass(frozen=True)
class UpdatePaymentGatewayCommand:
    gateway_id: UUID
    status: bool | None = None
    api_type: str | None = None
    currency: str | None = None
    convenience_type: str | None = None
    convenience_value: str | None = None
    configs: dict[str, str] | None = None


@dataclass(frozen=True)
class UpdateOtherApiCommand:
    other_api_id: UUID
    status: bool | None = None
    configs: dict[str, str] | None = None
