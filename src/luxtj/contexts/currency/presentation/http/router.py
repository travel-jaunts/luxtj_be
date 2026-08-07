from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from luxtj.bootstrap import config
from luxtj.contexts.currency.application.commands import (
    ActivateCurrencyCommand,
    DeactivateCurrencyCommand,
)
from luxtj.contexts.currency.application.use_cases import (
    CurrencyActivationService,
    CurrencyNotFoundError,
)
from luxtj.contexts.currency.bootstrap import build_currency_activation_service
from luxtj.contexts.currency.presentation.http.schemas import (
    ConversionRateEntrySerializer,
    CurrencyCodeBody,
    CurrencyItemSerializer,
    CurrencyListSerializer,
    DomainCurrencySerializer,
    PublicCurrencyRatesSerializer,
)
from luxtj.contexts.identity.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    require_permission,
)
from luxtj.shared_kernel.presentation.http.schemas import ApiSuccessResponse

admin_currencies_router = APIRouter(prefix="/currencies", tags=["admin-currencies"])
public_currencies_router = APIRouter(prefix="/currencies", tags=["currencies"])


@admin_currencies_router.post(
    "/list",
    response_model=ApiSuccessResponse[CurrencyListSerializer],
)
async def list_currencies(
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("currencies.view"))
    ],
    service: Annotated[CurrencyActivationService, Depends(build_currency_activation_service)],
) -> ApiSuccessResponse[CurrencyListSerializer]:
    items = await service.list_currencies()
    return ApiSuccessResponse(
        output=CurrencyListSerializer(
            items=[CurrencyItemSerializer.from_domain(i) for i in items],
            admin_currency=config.ADMIN_CURRENCY,
        )
    )


@admin_currencies_router.post(
    "/activate",
    response_model=ApiSuccessResponse[CurrencyItemSerializer],
)
async def activate_currency(
    body: Annotated[CurrencyCodeBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("currencies.edit"))
    ],
    service: Annotated[CurrencyActivationService, Depends(build_currency_activation_service)],
) -> ApiSuccessResponse[CurrencyItemSerializer]:
    try:
        item = await service.activate(ActivateCurrencyCommand(currency_code=body.currency_code))
    except CurrencyNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiSuccessResponse(output=CurrencyItemSerializer.from_domain(item))


@admin_currencies_router.post(
    "/deactivate",
    response_model=ApiSuccessResponse[CurrencyItemSerializer],
)
async def deactivate_currency(
    body: Annotated[CurrencyCodeBody, Body(...)],
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("currencies.edit"))
    ],
    service: Annotated[CurrencyActivationService, Depends(build_currency_activation_service)],
) -> ApiSuccessResponse[CurrencyItemSerializer]:
    try:
        item = await service.deactivate(
            DeactivateCurrencyCommand(currency_code=body.currency_code)
        )
    except CurrencyNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiSuccessResponse(output=CurrencyItemSerializer.from_domain(item))


@admin_currencies_router.post(
    "/refresh-rates",
    response_model=ApiSuccessResponse[dict],
)
async def refresh_currency_rates(
    _principal: Annotated[
        AuthenticatedPrincipal, Depends(require_permission("currencies.edit"))
    ],
    service: Annotated[CurrencyActivationService, Depends(build_currency_activation_service)],
) -> ApiSuccessResponse[dict]:
    from luxtj.contexts.currency.infrastructure.currency_conversion import get_currency_conversion

    conversion = get_currency_conversion()
    scraped = conversion.refresh_all_rates()
    return ApiSuccessResponse(
        output={
            "refreshed": len(scraped),
            "rates": [
                {"from": r.get("from"), "to": r.get("to"), "rate": r.get("rate")} for r in scraped
            ],
        }
    )


@public_currencies_router.post(
    "/rates",
    response_model=ApiSuccessResponse[PublicCurrencyRatesSerializer],
)
async def public_currency_rates(
    service: Annotated[CurrencyActivationService, Depends(build_currency_activation_service)],
) -> ApiSuccessResponse[PublicCurrencyRatesSerializer]:
    data = await service.get_public_rates()
    domain = data["domain_currency"]
    rates = {
        code: ConversionRateEntrySerializer(
            value=entry.get("value"),
            symbol=str(entry.get("symbol") or ""),
        )
        for code, entry in data["conversion_rate"].items()
    }
    return ApiSuccessResponse(
        output=PublicCurrencyRatesSerializer(
            domain_currency=DomainCurrencySerializer(
                code=domain["code"],
                symbol=domain["symbol"],
            ),
            conversion_rate=rates,
        )
    )
