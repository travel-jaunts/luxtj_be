from __future__ import annotations

import hashlib
import re
from typing import Any

from .parser import localized_string


def build_dedupe_key(name: str, region_type: str, country_name: str, country_code: str) -> str:
    norm_name = re.sub(r"\s+", " ", name.strip().lower())
    norm_type = (region_type.strip().lower() if region_type.strip() else "unknown")
    norm_country = country_name.strip().lower()
    norm_code = country_code.strip().lower()
    payload = f"{norm_name}|{norm_type}|{norm_country}|{norm_code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_region_row(row: dict[str, Any]) -> dict[str, Any] | None:
    name = localized_string(row.get("name"))
    if not name:
        return None
    center = row.get("center") if isinstance(row.get("center"), dict) else {}
    iata = str(row.get("iata") or "").strip()
    return {
        "name": name,
        "type": (str(row.get("type") or "Unknown").strip() or "Unknown"),
        "iata": iata[:3] if iata else None,
        "latitude": center.get("latitude"),
        "longitude": center.get("longitude"),
        "country_name": localized_string(row.get("country_name")),
        "country_code": str(row.get("country_code") or "").strip().upper(),
    }
