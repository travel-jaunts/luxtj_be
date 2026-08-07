"""In-process forever cache for active integration entities (Layer C)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import UUID

from luxtj.contexts.integration.domain.catalog import (
    OTHER_APIS,
    PAYMENT_GATEWAYS,
    SUB_MODULES_AND_BOOKING_APIS,
)
from luxtj.contexts.integration.domain.entities import (
    BookingApi,
    Module,
    OtherApi,
    PaymentGateway,
    SubModule,
)


@dataclass
class IntegrationRegistryCache:
    active_modules: dict[str, Module] = field(default_factory=dict)
    active_sub_modules: dict[str, SubModule] = field(default_factory=dict)
    active_booking_apis: dict[str, BookingApi] = field(default_factory=dict)
    active_payment_gateways: dict[str, PaymentGateway] = field(default_factory=dict)
    active_other_apis: dict[str, OtherApi] = field(default_factory=dict)
    _sub_module_by_id: dict[UUID, SubModule] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def replace(
        self,
        *,
        modules: list[Module],
        sub_modules: list[SubModule],
        booking_apis: list[BookingApi],
        payment_gateways: list[PaymentGateway],
        other_apis: list[OtherApi],
    ) -> None:
        sub_by_id = {s.id: s for s in sub_modules}
        active_modules = {m.name: m for m in modules if m.status}
        active_sub = {s.name: s for s in sub_modules if s.status}
        active_booking: dict[str, BookingApi] = {}
        for api in booking_apis:
            parent = sub_by_id.get(api.sub_module_id)
            if api.status and parent is not None and parent.status:
                catalog = SUB_MODULES_AND_BOOKING_APIS.get(parent.name, {})
                if api.code not in catalog:
                    continue
                key = f"{parent.name}:{api.code}"
                active_booking[key] = api
                active_booking[api.code] = api
        active_pg = {
            g.code: g for g in payment_gateways if g.status and g.code in PAYMENT_GATEWAYS
        }
        active_other = {o.code: o for o in other_apis if o.status and o.code in OTHER_APIS}
        with self._lock:
            self.active_modules = active_modules
            self.active_sub_modules = active_sub
            self.active_booking_apis = active_booking
            self.active_payment_gateways = active_pg
            self.active_other_apis = active_other
            self._sub_module_by_id = sub_by_id

    def resolve_booking_api(self, code: str, *, sub_module: str | None = None) -> BookingApi | None:
        with self._lock:
            if sub_module:
                return self.active_booking_apis.get(f"{sub_module}:{code}")
            return self.active_booking_apis.get(code)

    def resolve_payment_gateway(self, code: str) -> PaymentGateway | None:
        with self._lock:
            return self.active_payment_gateways.get(code)

    def list_active_payment_gateways(self) -> list[PaymentGateway]:
        with self._lock:
            return list(self.active_payment_gateways.values())

    def resolve_other_api(self, code: str) -> OtherApi | None:
        with self._lock:
            return self.active_other_apis.get(code)


_REGISTRY = IntegrationRegistryCache()


def get_integration_registry() -> IntegrationRegistryCache:
    return _REGISTRY
