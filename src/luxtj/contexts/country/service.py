"""Reusable country catalog service (CSV-backed).

Use from flight, hotel, identity, payments, etc. — not tied to any supplier.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from luxtj.contexts.country.domain import Country


def _countries_csv_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "countries.csv"


class CountryService:
    """Lookup helpers over the packaged countries catalog."""

    def __init__(self, countries: list[Country]) -> None:
        self._countries = countries
        self._by_iso2 = {c.iso2: c for c in countries if c.iso2}
        self._by_iso3 = {c.iso3: c for c in countries if c.iso3}

    @classmethod
    def from_csv(cls, path: Path | None = None) -> CountryService:
        csv_path = path or _countries_csv_path()
        rows: list[Country] = []
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                iso2 = str(row.get("iso2") or "").strip().upper()
                iso3 = str(row.get("iso3") or "").strip().upper()
                if not iso2 and not iso3:
                    continue
                rows.append(
                    Country(
                        name=str(row.get("name") or "").strip(),
                        iso2=iso2,
                        iso3=iso3,
                        phone_code=str(row.get("phonecode") or "").strip(),
                        nationality=str(row.get("nationality") or "").strip(),
                        currency=str(row.get("currency") or "").strip().upper(),
                        emoji=str(row.get("emoji") or "").strip(),
                    )
                )
        return cls(rows)

    def list_countries(self) -> list[Country]:
        return list(self._countries)

    def get_by_iso2(self, code: str | None) -> Country | None:
        text = str(code or "").strip().upper()
        return self._by_iso2.get(text) if text else None

    def get_by_iso3(self, code: str | None) -> Country | None:
        text = str(code or "").strip().upper()
        return self._by_iso3.get(text) if text else None

    def resolve(self, code: str | None) -> Country | None:
        """Resolve by ISO-2 or ISO-3."""
        text = str(code or "").strip().upper()
        if not text:
            return None
        if len(text) == 2:
            return self.get_by_iso2(text)
        if len(text) == 3:
            return self.get_by_iso3(text)
        return None

    def to_iso3(self, code: str | None, default: str = "IND") -> str:
        """Return ISO-3166 alpha-3. Accepts ISO-2 or ISO-3 input."""
        text = str(code or "").strip().upper()
        if len(text) == 3:
            return text
        if len(text) == 2:
            country = self.get_by_iso2(text)
            return country.iso3 if country and country.iso3 else default
        return default

    def to_iso2(self, code: str | None, default: str = "IN") -> str:
        """Return ISO-3166 alpha-2. Accepts ISO-2 or ISO-3 input."""
        text = str(code or "").strip().upper()
        if len(text) == 2:
            return text
        if len(text) == 3:
            country = self.get_by_iso3(text)
            return country.iso2 if country and country.iso2 else default
        return default

    def phone_code(self, code: str | None, default: str = "91") -> str:
        country = self.resolve(code)
        if country and country.phone_code:
            return country.phone_code
        return default


@lru_cache(maxsize=1)
def get_country_service() -> CountryService:
    """Process-wide singleton loaded from packaged countries.csv."""
    return CountryService.from_csv()
