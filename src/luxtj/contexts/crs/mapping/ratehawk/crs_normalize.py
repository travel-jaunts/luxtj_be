"""Flatten supplier hotel/room content into generic CRS columns + child rows.

Keeps RateHawk-specific shapes at the edge; CRS tables stay supplier-agnostic.
"""

from __future__ import annotations

from typing import Any

_VIEW_LABELS: dict[int, str] = {
    1: "bay",
    2: "bosphorus",
    3: "city",
    4: "courtyard",
    5: "garden",
    6: "harbour",
    7: "lake",
    8: "mountain",
    9: "ocean",
    10: "park",
    11: "pool",
    12: "river",
    13: "sea",
    14: "street",
    15: "panoramic",
    16: "various",
    17: "with-view",
    18: "beachfront",
    19: "oceanfront",
    20: "seafront",
}

_CLASS_LABELS: dict[int, str] = {
    0: "run-of-house",
    1: "dorm",
    2: "capsule",
    3: "room",
    4: "junior-suite",
    5: "suite",
    6: "apartment",
    7: "studio",
    8: "villa",
    9: "cottage",
    17: "bungalow",
    18: "chalet",
    19: "camping",
    20: "tent",
}

_QUALITY_LABELS: dict[int, str] = {
    1: "economy",
    2: "standard",
    3: "comfort",
    4: "business",
    5: "superior",
    6: "deluxe",
    7: "premier",
    8: "executive",
    9: "presidential",
    17: "premium",
    18: "classic",
    19: "ambassador",
    20: "grand",
    21: "luxury",
    22: "platinum",
    23: "prestige",
    24: "privilege",
    25: "royal",
}

_GENDER_LABELS: dict[int, str] = {
    1: "male",
    2: "female",
    3: "mixed",
}

_FLOOR_LABELS: dict[int, str] = {
    1: "penthouse",
    2: "duplex",
    3: "basement",
    4: "attic",
}

_BEDDING_LABELS: dict[int, str] = {
    1: "bunk",
    2: "single",
    3: "double",
    4: "twin",
    7: "multiple",
    8: "chair-bed",
    9: "sofa",
}

_BATHROOM_LABELS: dict[int, str] = {
    1: "shared",
    2: "private",
    3: "external_private",
}


def _clip(value: Any, limit: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:limit]


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except TypeError, ValueError:
        return None
    return n if n != 0 else None


def _join_list(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    parts = [str(v).strip() for v in value if str(v).strip()]
    return ",".join(parts) if parts else None


def flatten_hotel_content(hotel: dict[str, Any]) -> dict[str, Any]:
    """Return CRS hotel scalar fields + child-row payloads (no JSON blobs)."""
    facts = hotel.get("facts") if isinstance(hotel.get("facts"), dict) else {}
    electricity = facts.get("electricity") if isinstance(facts.get("electricity"), dict) else {}
    register = facts.get("register") if isinstance(facts.get("register"), dict) else {}
    keys = hotel.get("keys_pickup") if isinstance(hotel.get("keys_pickup"), dict) else {}
    cert = hotel.get("star_certificate") if isinstance(hotel.get("star_certificate"), dict) else {}

    floors = _int_or_none(facts.get("floors_number"))
    rooms = _int_or_none(facts.get("rooms_number"))
    year_built = _int_or_none(facts.get("year_built"))
    year_renovated = _int_or_none(facts.get("year_renovated"))

    description_sections: list[dict[str, Any]] = []
    desc_struct = hotel.get("description_struct")
    if isinstance(desc_struct, list):
        for idx, block in enumerate(desc_struct):
            if not isinstance(block, dict):
                continue
            paragraphs = block.get("paragraphs") or []
            body = "\n\n".join(
                str(p).strip() for p in paragraphs if isinstance(p, str) and p.strip()
            )
            if not body:
                continue
            description_sections.append(
                {
                    "title": _clip(block.get("title"), 255),
                    "body": body,
                    "sort_order": idx,
                }
            )

    payment_methods: list[str] = []
    raw_pay = hotel.get("payment_methods")
    if isinstance(raw_pay, list):
        for m in raw_pay:
            code = _clip(m, 50)
            if code:
                payment_methods.append(code)

    feature_tags: list[str] = []
    raw_tags = hotel.get("serp_filters")
    if isinstance(raw_tags, list):
        for t in raw_tags:
            tag = _clip(t, 100)
            if tag:
                feature_tags.append(tag)

    policy_sections: list[dict[str, Any]] = []
    for idx, block in enumerate(hotel.get("policy_struct") or []):
        if not isinstance(block, dict):
            continue
        paragraphs = block.get("paragraphs") or []
        body = "\n\n".join(str(p).strip() for p in paragraphs if isinstance(p, str) and p.strip())
        if not body and not block.get("title"):
            continue
        policy_sections.append(
            {
                "section_type": "policy",
                "title": _clip(block.get("title"), 255),
                "body": body or str(block.get("title") or ""),
                "sort_order": idx,
            }
        )
    extra = str(hotel.get("metapolicy_extra_info") or "").strip()
    if extra:
        policy_sections.append(
            {
                "section_type": "extra",
                "title": "Additional policy info",
                "body": extra,
                "sort_order": len(policy_sections),
            }
        )

    policy_items: list[dict[str, Any]] = []
    meta = (
        hotel.get("metapolicy_struct") if isinstance(hotel.get("metapolicy_struct"), dict) else {}
    )
    for category, value in meta.items():
        items: list[Any]
        if isinstance(value, list):
            items = value
        elif isinstance(value, dict) and value:
            items = [value]
        else:
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            attrs = {
                str(k): ("" if v is None else str(v))
                for k, v in item.items()
                if not isinstance(v, (dict, list))
            }
            if not attrs:
                continue
            policy_items.append(
                {"category": _clip(category, 80) or "other", "sort_order": idx, "attrs": attrs}
            )

    register_rooms: list[dict[str, Any]] = []
    for idx, row in enumerate(register.get("rooms") or []):
        if not isinstance(row, dict):
            continue
        register_rooms.append(
            {
                "category_type": _clip(row.get("category_type"), 100),
                "rooms_count": _int_or_none(row.get("rooms_count")),
                "sort_order": idx,
            }
        )

    contactless = keys.get("is_contactless")
    return {
        "floors_count": floors,
        "rooms_count": rooms,
        "year_built": year_built,
        "year_renovated": year_renovated,
        "electricity_frequency": _join_list(electricity.get("frequency")),
        "electricity_voltage": _join_list(electricity.get("voltage")),
        "electricity_sockets": _join_list(electricity.get("sockets")),
        "star_certificate_id": _clip(cert.get("certificate_id"), 100),
        "star_certificate_valid_to": _clip(cert.get("valid_to"), 40),
        "keys_pickup_type": _clip(keys.get("type"), 50),
        "keys_pickup_phone": _clip(keys.get("phone"), 50),
        "keys_pickup_email": _clip(keys.get("email"), 255),
        "keys_pickup_is_contactless": bool(contactless) if contactless is not None else None,
        "keys_pickup_address": _clip(keys.get("apartment_office_address"), 500),
        "keys_pickup_extra_info": str(keys.get("apartment_extra_information") or "").strip()
        or None,
        "register_record": _clip(register.get("record"), 100),
        "register_link": _clip(register.get("link"), 2048),
        "register_email": _clip(register.get("email"), 255),
        "register_phone": _clip(register.get("phone"), 50),
        "register_status": _clip(register.get("status"), 50),
        "register_kind": _clip(register.get("kind"), 50),
        "register_name": _clip(register.get("name"), 255),
        "register_address": _clip(register.get("address"), 500),
        "register_status_end_date": _clip(register.get("status_end_date"), 40),
        "register_taxpayer_number": _clip(register.get("taxpayer_number"), 30),
        "register_state_registration_number": _clip(register.get("state_registration_number"), 30),
        "register_work_time": _clip(register.get("work_time"), 255),
        "external_code": _clip(hotel.get("supplier_slug") or hotel.get("id"), 255)
        if not isinstance(hotel.get("id"), (int, float))
        else _clip(hotel.get("supplier_slug"), 255),
        "description_sections": description_sections,
        "payment_methods": payment_methods,
        "feature_tags": feature_tags,
        "policy_sections": policy_sections,
        "policy_items": policy_items,
        "register_rooms": register_rooms,
    }


def flatten_room_group(rg: dict[str, Any]) -> dict[str, Any]:
    """Map room dump (+ rg_ext / name_struct) onto flat CRS room columns."""
    rg_ext = rg.get("rg_ext") if isinstance(rg.get("rg_ext"), dict) else {}
    name_struct = rg.get("name_struct") if isinstance(rg.get("name_struct"), dict) else {}

    bedding_code = _int_or_none(rg_ext.get("bedding"))
    bathroom_code = _int_or_none(rg_ext.get("bathroom"))
    balcony_code = _int_or_none(rg_ext.get("balcony"))
    capacity = _int_or_none(rg_ext.get("capacity"))
    bedrooms = _int_or_none(rg_ext.get("bedrooms"))
    view_code = _int_or_none(rg_ext.get("view"))
    room_class = _int_or_none(rg_ext.get("class"))
    quality = _int_or_none(rg_ext.get("quality"))
    sex = _int_or_none(rg_ext.get("sex"))
    family = _int_or_none(rg_ext.get("family"))
    club = _int_or_none(rg_ext.get("club"))
    floor = _int_or_none(rg_ext.get("floor"))

    bedding_type = _BEDDING_LABELS.get(bedding_code) if bedding_code else None
    bathroom_type = _BATHROOM_LABELS.get(bathroom_code) if bathroom_code else None
    # Prefer human strings from name_struct when present
    ns_bedding = str(name_struct.get("bedding_type") or "").strip()
    ns_bath = str(name_struct.get("bathroom") or "").strip()
    if ns_bedding:
        bedding_type = ns_bedding[:100]
    if ns_bath:
        bathroom_type = ns_bath[:100]

    size = None
    if rg.get("size") is not None and rg.get("size") != "":
        try:
            size = float(rg["size"])
        except TypeError, ValueError:
            size = None

    main_name = str(rg.get("main_name") or name_struct.get("main_name") or "").strip() or None

    return {
        "main_name": main_name[:255] if main_name else None,
        "description": str(rg.get("description") or "").strip() or None,
        "bedding_type": bedding_type,
        "bathroom_type": bathroom_type,
        "size": size,
        "capacity": capacity,
        "bedrooms": bedrooms,
        "balcony": True if balcony_code == 1 else (False if balcony_code == 0 else None),
        "view_code": view_code,
        "view_type": (
            _VIEW_LABELS.get(view_code)
            if view_code is not None and view_code in _VIEW_LABELS
            else (str(view_code) if view_code else None)
        ),
        "room_class": room_class,
        "class_label": _CLASS_LABELS.get(room_class) if room_class is not None else None,
        "quality": quality,
        "quality_label": _QUALITY_LABELS.get(quality) if quality is not None else None,
        "gender": _GENDER_LABELS.get(sex) if sex else None,
        "is_family": True if family == 1 else (False if family == 0 else None),
        "is_club": True if club == 1 else (False if club == 0 else None),
        "floor_type": _FLOOR_LABELS.get(floor) if floor else None,
    }
