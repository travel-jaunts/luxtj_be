"""Airport IATA catalog loaded from assets/data/airports.csv."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AirportRecord:
    iata: str
    name: str
    city: str
    country: str


def _airports_csv_path() -> Path:
    # .../luxtj_be/src/luxtj/contexts/flight/infrastructure/airport_catalog.py
    # parents[5] = luxtj_be
    return Path(__file__).resolve().parents[5] / "assets" / "data" / "airports.csv"


@lru_cache(maxsize=1)
def load_airports() -> tuple[AirportRecord, ...]:
    path = _airports_csv_path()
    if not path.is_file():
        return ()
    rows: list[AirportRecord] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            iata = str(row.get("iata") or "").strip().upper()
            if not iata or iata == "\\N" or len(iata) != 3:
                continue
            rows.append(
                AirportRecord(
                    iata=iata,
                    name=str(row.get("name") or "").strip(),
                    city=str(row.get("city") or "").strip(),
                    country=str(row.get("country") or "").strip(),
                )
            )
    return tuple(rows)


def search_airports(query: str, *, limit: int = 20) -> list[AirportRecord]:
    q = (query or "").strip().lower()
    if len(q) < 1:
        return []
    limit = max(1, min(int(limit or 20), 50))
    airports = load_airports()
    exact: list[AirportRecord] = []
    prefix: list[AirportRecord] = []
    contains: list[AirportRecord] = []
    for a in airports:
        iata_l = a.iata.lower()
        blob = f"{a.iata} {a.name} {a.city} {a.country}".lower()
        if iata_l == q:
            exact.append(a)
        elif iata_l.startswith(q) or a.city.lower().startswith(q):
            prefix.append(a)
        elif q in blob:
            contains.append(a)
        if len(exact) + len(prefix) >= limit:
            break
    out = exact + prefix + contains
    # de-dupe by iata preserving order
    seen: set[str] = set()
    deduped: list[AirportRecord] = []
    for a in out:
        if a.iata in seen:
            continue
        seen.add(a.iata)
        deduped.append(a)
        if len(deduped) >= limit:
            break
    return deduped
