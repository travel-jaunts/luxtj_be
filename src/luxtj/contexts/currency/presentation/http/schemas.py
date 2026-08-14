from pydantic import Field

from luxtj.contexts.currency.domain.entities import CurrencyListItem
from luxtj.shared_kernel.presentation.http.schemas import ApiSerializerBaseModel


class CurrencyCodeBody(ApiSerializerBaseModel):
    currency_code: str = Field(..., min_length=3, max_length=3, description="ISO-4217 code")


class CurrencyItemSerializer(ApiSerializerBaseModel):
    code: str
    currency_name: str
    currency_symbol: str
    active: bool

    @classmethod
    def from_domain(cls, item: CurrencyListItem) -> CurrencyItemSerializer:
        return cls(
            code=item.code,
            currency_name=item.currency_name,
            currency_symbol=item.currency_symbol,
            active=item.active,
        )


class CurrencyListSerializer(ApiSerializerBaseModel):
    items: list[CurrencyItemSerializer]
    admin_currency: str


class DomainCurrencySerializer(ApiSerializerBaseModel):
    code: str
    symbol: str


class ConversionRateEntrySerializer(ApiSerializerBaseModel):
    value: float | None = None
    symbol: str = ""


class PublicCurrencyRatesSerializer(ApiSerializerBaseModel):
    domain_currency: DomainCurrencySerializer
    conversion_rate: dict[str, ConversionRateEntrySerializer]
