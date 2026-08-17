from uuid import UUID

from pydantic import Field

from luxtj.contexts.integration.domain.entities import (
    BookingApi,
    Module,
    OtherApi,
    PaymentGateway,
    SubModule,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class ModuleSerializer(ApiSerializerBaseModel):
    id: UUID
    name: str
    status: bool

    @classmethod
    def from_domain(cls, entity: Module) -> ModuleSerializer:
        return cls(id=entity.id, name=entity.name, status=entity.status)


class SubModuleSerializer(ApiSerializerBaseModel):
    id: UUID
    name: str
    status: bool

    @classmethod
    def from_domain(cls, entity: SubModule) -> SubModuleSerializer:
        return cls(id=entity.id, name=entity.name, status=entity.status)


class CatalogFieldSerializer(ApiSerializerBaseModel):
    name: str
    configs: list[str]
    config_keys: list[str]
    lib_name: str | None = None
    auth_required: bool | None = None
    currency: str | None = None
    refund_api: str | None = None


class BookingApiSerializer(ApiSerializerBaseModel):
    id: UUID
    sub_module_id: UUID
    sub_module_name: str | None = None
    code: str
    name: str
    status: bool
    api_type: str | None = None
    currency: str | None = None
    configs: dict[str, str]
    catalog: CatalogFieldSerializer | None = None

    @classmethod
    def from_overview(cls, item: dict) -> BookingApiSerializer:
        entity: BookingApi = item["entity"]
        catalog = item.get("catalog")
        return cls(
            id=entity.id,
            sub_module_id=entity.sub_module_id,
            sub_module_name=item.get("subModuleName"),
            code=entity.code,
            name=entity.name,
            status=entity.status,
            api_type=entity.api_type,
            currency=entity.currency,
            configs=entity.credential_configs(),
            catalog=CatalogFieldSerializer(**catalog) if catalog else None,
        )


class PaymentGatewaySerializer(ApiSerializerBaseModel):
    id: UUID
    code: str
    name: str
    status: bool
    api_type: str | None = None
    currency: str | None = None
    convenience_type: str | None = None
    convenience_value: str | None = None
    configs: dict[str, str]
    catalog: CatalogFieldSerializer | None = None

    @classmethod
    def from_overview(cls, item: dict) -> PaymentGatewaySerializer:
        entity: PaymentGateway = item["entity"]
        catalog = item.get("catalog")
        return cls(
            id=entity.id,
            code=entity.code,
            name=entity.name,
            status=entity.status,
            api_type=entity.api_type,
            currency=entity.currency,
            convenience_type=entity.convenience_type,
            convenience_value=entity.convenience_value,
            configs=entity.credential_configs(),
            catalog=CatalogFieldSerializer(**catalog) if catalog else None,
        )


class OtherApiSerializer(ApiSerializerBaseModel):
    id: UUID
    code: str
    name: str
    status: bool
    configs: dict[str, str]
    catalog: CatalogFieldSerializer | None = None

    @classmethod
    def from_overview(cls, item: dict) -> OtherApiSerializer:
        entity: OtherApi = item["entity"]
        catalog = item.get("catalog")
        return cls(
            id=entity.id,
            code=entity.code,
            name=entity.name,
            status=entity.status,
            configs=entity.credential_configs(),
            catalog=CatalogFieldSerializer(**catalog) if catalog else None,
        )


class IntegrationsCurrencyOptionSerializer(ApiSerializerBaseModel):
    code: str
    currency_name: str
    currency_symbol: str
    active: bool


class IntegrationsOverviewSerializer(ApiSerializerBaseModel):
    modules: list[ModuleSerializer]
    sub_modules: list[SubModuleSerializer]
    booking_apis: list[BookingApiSerializer]
    payment_gateways: list[PaymentGatewaySerializer]
    other_apis: list[OtherApiSerializer]
    currencies: list[IntegrationsCurrencyOptionSerializer] = []


class StatusBody(ApiSerializerBaseModel):
    status: bool


class UpdateBookingApiBody(ApiSerializerBaseModel):
    status: bool | None = None
    api_type: str | None = Field(None, max_length=10)
    currency: str | None = Field(None, max_length=10)
    configs: dict[str, str] | None = None


class UpdatePaymentGatewayBody(ApiSerializerBaseModel):
    status: bool | None = None
    api_type: str | None = Field(None, max_length=10)
    currency: str | None = Field(None, max_length=10)
    convenience_type: str | None = Field(None, max_length=20)
    convenience_value: str | None = None
    configs: dict[str, str] | None = None


class UpdateOtherApiBody(ApiSerializerBaseModel):
    status: bool | None = None
    configs: dict[str, str] | None = None
