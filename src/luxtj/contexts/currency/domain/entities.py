from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from luxtj.utils import timeutils


@dataclass
class CurrencyMeta:
    code: str
    currency_name: str
    currency_symbol: str


@dataclass
class ActiveCurrency:
    id: UUID
    currency_code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, currency_code: str, now: datetime | None = None) -> "ActiveCurrency":
        ts = now or timeutils.datetime_now()
        return cls(
            id=uuid4(),
            currency_code=currency_code.upper().strip(),
            created_at=ts,
            updated_at=ts,
        )


@dataclass
class CurrencyListItem:
    code: str
    currency_name: str
    currency_symbol: str
    active: bool
