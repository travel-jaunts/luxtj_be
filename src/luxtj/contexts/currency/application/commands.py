from dataclasses import dataclass


@dataclass(frozen=True)
class ActivateCurrencyCommand:
    currency_code: str


@dataclass(frozen=True)
class DeactivateCurrencyCommand:
    currency_code: str
