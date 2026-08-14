from __future__ import annotations

import html
import json
from typing import Any


def _pv(item: dict[str, Any], key: str, fallback: str = "unspecified") -> str:
    raw = item.get(key)
    if raw is None:
        return fallback
    text = str(raw).strip()
    return text if text else fallback


def _pv_any(item: dict[str, Any], keys: list[str], fallback: str = "unspecified") -> str:
    for key in keys:
        raw = item.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return fallback


def _to_policy_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        if isinstance(value, dict) and value:
            return [value]
        return []
    return [v for v in value if isinstance(v, dict)]


def build_policy_text(hotel: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for block in hotel.get("policy_struct") or []:
        if not isinstance(block, dict):
            continue
        title = str(block.get("title") or "").strip()
        paragraphs = block.get("paragraphs") or []
        paragraph_text = "\n".join(str(p).strip() for p in paragraphs if str(p).strip()).strip()
        if title:
            parts.append(title)
        if paragraph_text:
            parts.append(paragraph_text)

    extra = str(hotel.get("metapolicy_extra_info") or "").strip()
    if extra:
        parts.append(extra)

    out = "\n\n".join(parts).strip()
    return out if out else None


def build_hotel_policies_html(hotel: dict[str, Any]) -> str | None:
    meta = (
        hotel.get("metapolicy_struct") if isinstance(hotel.get("metapolicy_struct"), dict) else {}
    )
    points: list[str] = []

    for item in _to_policy_items(meta.get("deposit")):
        points.append(
            f"Deposit is {_pv(item, 'availability')} to have. "
            f"{_pv_any(item, ['deposit_type', 'type'])} {_pv(item, 'payment_type')} "
            f"{_pv(item, 'pricing_method')}. The price is {_pv(item, 'price')} "
            f"{_pv(item, 'currency')} {_pv(item, 'price_unit')}."
        )

    for item in _to_policy_items(meta.get("internet")):
        points.append(
            f"{_pv(item, 'type')} is {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} "
            f"{_pv(item, 'price_unit')}. {_pv(item, 'work_area')}."
        )

    for item in _to_policy_items(meta.get("meal")):
        points.append(
            f"{_pv(item, 'type')} is {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} per a person."
        )

    for item in _to_policy_items(meta.get("children_meal")):
        points.append(
            f"{_pv(item, 'type')} is {_pv(item, 'inclusion')} to the overall price. "
            f"For children of {_pv(item, 'age_start')}-{_pv(item, 'age_end')} y.o. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} per a child."
        )

    for item in _to_policy_items(meta.get("extra_bed")):
        points.append(
            f"{_pv(item, 'amount')} bed(s). {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} {_pv(item, 'price_unit')}."
        )

    for item in _to_policy_items(meta.get("cot")):
        points.append(
            f"{_pv(item, 'amount')} cot(s). {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} {_pv(item, 'price_unit')}."
        )

    for item in _to_policy_items(meta.get("pets")):
        points.append(
            f"Pet weight is {_pv(item, 'pets_type')} is {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} {_pv(item, 'price_unit')}."
        )

    for item in _to_policy_items(meta.get("shuttle")):
        points.append(
            f"Shuttle is {_pv(item, 'shuttle_type')} to {_pv(item, 'destination_type')}. "
            f"{_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')}."
        )

    for item in _to_policy_items(meta.get("parking")):
        points.append(
            f"Parking is {_pv(item, 'territory_type')} and {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} {_pv(item, 'price_unit')}."
        )

    for item in _to_policy_items(meta.get("children")):
        points.append(
            f"Bed for a child is {_pv(item, 'extra_bed')}. "
            f"For children of {_pv(item, 'age_start')}-{_pv(item, 'age_end')} y.o. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')}."
        )

    for item in _to_policy_items(meta.get("visa")):
        points.append(f"Visa support for the embassy is {_pv(item, 'visa_support')}.")

    for item in _to_policy_items(meta.get("no_show")):
        points.append(
            f"No-show is {_pv(item, 'availability')} to have {_pv(item, 'day_period')} at {_pv(item, 'time')}."
        )

    for item in _to_policy_items(meta.get("add_fee")):
        points.append(
            f"Additional service is for {_pv(item, 'fee_type')}. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')} {_pv(item, 'price_unit')}."
        )

    for item in _to_policy_items(meta.get("check_in_check_out")):
        points.append(
            f"{_pv(item, 'check_in_check_out_type')} is {_pv(item, 'inclusion')} to the overall price. "
            f"The price is {_pv(item, 'price')} {_pv(item, 'currency')}."
        )

    parts: list[str] = []
    extra_info = str(hotel.get("metapolicy_extra_info") or "").strip()
    if extra_info:
        parts.append(f"<p>{html.escape(extra_info).replace(chr(10), '<br>')}</p>")

    if points:
        items = "".join(f"<li>{html.escape(line)}</li>" for line in points)
        parts.append(f"<ul>{items}</ul>")

    out = "\n".join(parts).strip()
    return out if out else None


def build_meta_payload(hotel: dict[str, Any]) -> str | None:
    """Teenva-compatible CRS hotel.meta JSON.

    Stores metapolicy_struct (structured RateHawk policies) plus facts /
    payment_methods / serp_filters when present.
    """
    meta = {
        "facts": hotel.get("facts"),
        "payment_methods": hotel.get("payment_methods"),
        "metapolicy_struct": hotel.get("metapolicy_struct"),
        "serp_filters": hotel.get("serp_filters"),
        # Convenience copies for admin / debugging (also live in dedicated columns).
        "policy_struct": hotel.get("policy_struct"),
        "metapolicy_extra_info": hotel.get("metapolicy_extra_info"),
    }
    if not any(v for v in meta.values() if v):
        return None
    return json.dumps(meta, ensure_ascii=False)
