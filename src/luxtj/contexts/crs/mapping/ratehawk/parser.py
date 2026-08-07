from __future__ import annotations

import hashlib
import json
import re
from typing import Any


RATEHAWK_IMAGE_SIZE = "1024x768"

# RateHawk rg_ext code → human label (docs: architecture-docs/ratehawk-hotel.md)
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


def _clip(value: Any, limit: int) -> str:
    """Clip to a DB column width — dump values are unbounded and one oversized
    string fails the whole multi-row staging INSERT (StringDataRightTruncation)."""
    text = str(value or "")
    return text[:limit] if len(text) > limit else text


def resolve_ratehawk_image_url(url: str, size: str = RATEHAWK_IMAGE_SIZE) -> str:
    """Replace RateHawk CDN `{size}` placeholder (e.g. 1024x768 for fit)."""
    url = str(url or "").strip()
    if not url or "{size}" not in url:
        return url
    return url.replace("{size}", size)


def _resolve_room_images_list(raw: Any) -> list[str]:
    """RateHawk room_groups.images — string URL list (main image first)."""
    urls: list[str] = []
    if not isinstance(raw, list):
        return urls
    for img in raw:
        if isinstance(img, str) and img.strip():
            resolved = resolve_ratehawk_image_url(img)
            if resolved:
                urls.append(resolved)
        elif isinstance(img, dict):
            resolved = resolve_ratehawk_image_url(str(img.get("url") or ""))
            if resolved:
                urls.append(resolved)
    return urls


def _resolve_images_ext_list(raw: Any) -> list[dict[str, str]]:
    """RateHawk images_ext / room_groups.images_ext — gallery with category_slug."""
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for img in raw:
        if not isinstance(img, dict):
            continue
        url = resolve_ratehawk_image_url(str(img.get("url") or ""))
        if not url:
            continue
        out.append({"url": url, "category_slug": str(img.get("category_slug") or "")})
    return out


def _resolve_room_images_ext_list(raw: Any) -> list[dict[str, str]]:
    return _resolve_images_ext_list(raw)


def extract_hotel_images(hotel: dict[str, Any]) -> list[dict[str, str]]:
    """Prefer images_ext; fall back to deprecated images[]."""
    result: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, category_slug: str = "") -> None:
        resolved = resolve_ratehawk_image_url(str(url or "").strip())
        if not resolved or resolved in seen:
            return
        seen.add(resolved)
        result.append({"url": resolved, "category_slug": category_slug})

    for entry in _resolve_images_ext_list(hotel.get("images_ext")):
        add(entry["url"], entry["category_slug"])

    if not result:
        for url in hotel.get("images") or []:
            if isinstance(url, str) and url:
                add(url)
            elif isinstance(url, dict):
                add(str(url.get("url") or ""), str(url.get("category_slug") or ""))

    return result


def extract_room_images(room_group: dict[str, Any]) -> list[dict[str, str]]:
    """
    Merge room main images (images[]) and gallery (images_ext[]).
    Main URLs are listed first; gallery URLs follow, deduped by URL.
    """
    result: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, category_slug: str = "") -> None:
        resolved = resolve_ratehawk_image_url(str(url or "").strip())
        if not resolved or resolved in seen:
            return
        seen.add(resolved)
        result.append({"url": resolved, "category_slug": category_slug})

    for url in _resolve_room_images_list(room_group.get("images")):
        add(url)

    for entry in _resolve_room_images_ext_list(room_group.get("images_ext")):
        add(entry["url"], entry["category_slug"])

    return result


def collect_room_image_urls(room_group: dict[str, Any]) -> list[str]:
    return [entry["url"] for entry in extract_room_images(room_group)]


def localized_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("en", "EN"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        for item in value.values():
            if isinstance(item, str) and item.strip():
                return item.strip()
    return ""


def normalize_name(name: str) -> str:
    lowered = name.strip().lower()
    return re.sub(r"[^a-z0-9]", "", lowered)


def normalize_star_rating(value: Any) -> float:
    """Normalize stars to 0–5 (1 decimal). Supports 4EST, H4_5 → 4.5, and numerics."""
    if isinstance(value, (int, float)):
        return round(min(5.0, max(0.0, float(value))), 1)
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    # Hotelbeds half-star category codes: H3_5 → 3.5, H4_5 → 4.5
    half = re.match(r"^H(\d)_5$", raw, re.IGNORECASE)
    if half:
        return round(min(5.0, max(0.0, int(half.group(1)) + 0.5)), 1)
    if raw.replace(".", "", 1).isdigit():
        return round(min(5.0, max(0.0, float(raw))), 1)
    match = re.match(r"^(\d+(?:\.\d+)?)", raw)
    if match:
        return round(min(5.0, max(0.0, float(match.group(1)))), 1)
    return 0.0


def star_key_component(star: float) -> str:
    normalized = normalize_star_rating(star)
    if normalized % 1 == 0:
        return str(int(normalized))
    return f"{normalized:.1f}"


def compute_unique_key(name: str, star: float | int, region_id: str | int) -> str:
    payload = f"{normalize_name(name)}|{star_key_component(float(star))}|{region_id}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def split_address(address: str) -> tuple[str, str]:
    address = re.sub(r"\s+", " ", address.strip())
    if not address:
        return "", ""
    parts = re.split(r",\s*", address, maxsplit=1)
    line1 = parts[0].strip() if parts else ""
    line2 = parts[1].strip() if len(parts) > 1 else ""
    return line1, line2


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def derive_rg_ext_fields(rg_ext: dict[str, Any] | None) -> dict[str, Any]:
    """Map RateHawk rg_ext codes onto CRS room columns (all nullable)."""
    ext = rg_ext if isinstance(rg_ext, dict) else {}
    bedding_code = _int_or_none(ext.get("bedding"))
    bathroom_code = _int_or_none(ext.get("bathroom"))
    balcony_code = _int_or_none(ext.get("balcony"))
    capacity = _int_or_none(ext.get("capacity"))
    bedrooms = _int_or_none(ext.get("bedrooms"))
    # capacity/bedrooms 0 = undefined in RateHawk
    if capacity == 0:
        capacity = None
    if bedrooms == 0:
        bedrooms = None
    return {
        "bedding_type": _BEDDING_LABELS.get(bedding_code) if bedding_code else None,
        "bathroom_type": _BATHROOM_LABELS.get(bathroom_code) if bathroom_code else None,
        "capacity": capacity,
        "bedrooms": bedrooms,
        "balcony": True if balcony_code == 1 else (False if balcony_code == 0 else None),
        "view_code": _int_or_none(ext.get("view")),
        "room_class": _int_or_none(ext.get("class")),
        "quality": _int_or_none(ext.get("quality")),
    }


def _collect_amenity_entries(hotel: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (flat names for staging, blender allamenities with is_paid/group)."""
    names: list[str] = []
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, bool]] = set()

    for group in hotel.get("amenity_groups") or []:
        if not isinstance(group, dict):
            continue
        group_name = localized_string(group.get("group_name")) or "General"
        for amenity in group.get("amenities") or []:
            label = amenity if isinstance(amenity, str) else localized_string(amenity)
            if not label:
                continue
            key = (label, group_name, False)
            if key in seen:
                continue
            seen.add(key)
            names.append(label)
            entries.append({"name": label, "category": group_name, "is_paid": False})
        for amenity in group.get("non_free_amenities") or []:
            label = amenity if isinstance(amenity, str) else localized_string(amenity)
            if not label:
                continue
            key = (label, group_name, True)
            if key in seen:
                continue
            seen.add(key)
            names.append(label)
            entries.append({"name": label, "category": group_name, "is_paid": True})

    return names, entries


def _description_from_struct(description_struct: Any) -> str:
    if isinstance(description_struct, list) and description_struct:
        chunks: list[str] = []
        for block in description_struct:
            if not isinstance(block, dict):
                continue
            paragraphs = block.get("paragraphs") or []
            for p in paragraphs:
                if isinstance(p, str) and p.strip():
                    chunks.append(p.strip())
        if chunks:
            return "\n\n".join(chunks)
    return ""


def parse_for_staging(
    hotel: dict[str, Any], region_id: str | int | None = None
) -> dict[str, Any] | None:
    # deleted = permanently gone; is_closed = still catalogued (show as closed).
    if hotel.get("deleted"):
        return None

    hid = str(hotel.get("hid") or hotel.get("id") or "")
    name = localized_string(hotel.get("name"))
    if not hid or not name:
        return None
    hid = _clip(hid, 64)
    name = _clip(name, 255)

    resolved_region_id = str(region_id).strip() if region_id else ""
    star = normalize_star_rating(hotel.get("star_rating") or hotel.get("stars") or 0)
    address = localized_string(hotel.get("address"))
    line1, line2 = split_address(address)

    hotel_image_entries = extract_hotel_images(hotel)
    image_urls = [e["url"] for e in hotel_image_entries]

    amenity_names, amenity_entries = _collect_amenity_entries(hotel)

    kind = _clip(localized_string(hotel.get("kind")) or str(hotel.get("kind") or ""), 100)
    hotel_chain = _clip(localized_string(hotel.get("hotel_chain")), 255)
    check_in = _clip(hotel.get("check_in_time"), 20) or None
    check_in_end = _clip(hotel.get("check_in_time_end"), 20) or None
    check_out = _clip(hotel.get("check_out_time"), 20) or None
    fd_start = _clip(hotel.get("front_desk_time_start"), 20) or None
    fd_end = _clip(hotel.get("front_desk_time_end"), 20) or None

    rooms: list[dict[str, Any]] = []
    room_payload: list[dict[str, Any]] = []
    seen_room_ids: set[str] = set()
    for rg in hotel.get("room_groups") or []:
        if not isinstance(rg, dict):
            continue
        rg_id = str(rg.get("room_group_id") or rg.get("id") or "")
        if not rg_id or rg_id in seen_room_ids:
            continue
        seen_room_ids.add(rg_id)
        room_image_entries = extract_room_images(rg)
        room_images = [entry["url"] for entry in room_image_entries]
        room_amenities = (
            rg.get("room_amenities") if isinstance(rg.get("room_amenities"), list) else []
        )
        rg_ext = rg.get("rg_ext") if isinstance(rg.get("rg_ext"), dict) else None
        name_struct = rg.get("name_struct") if isinstance(rg.get("name_struct"), dict) else None
        main_name = localized_string(rg.get("main_name"))
        if not main_name and isinstance(name_struct, dict):
            main_name = localized_string(name_struct.get("main_name"))
        room_name = localized_string(rg.get("name")) or main_name
        room_desc = localized_string(rg.get("description"))
        rooms.append(
            {
                "supplier_hotel_code": hid,
                "room_group_id": _clip(rg_id, 64),
                "name": _clip(room_name, 255),
                "main_name": _clip(main_name, 255) or None,
                "description": room_desc,
                "amenity_slugs": room_amenities,
                "image_urls": room_images,
                "rg_ext": rg_ext,
                "name_struct": name_struct,
                "images_ext": room_image_entries,
            }
        )
        room_payload.append(
            {
                "room_group_id": rg_id,
                "name": room_name,
                "main_name": main_name or None,
                "description": room_desc,
                "images": _resolve_room_images_list(rg.get("images")),
                "images_ext": room_image_entries,
                "room_amenities": room_amenities,
                "rg_ext": rg_ext,
                "name_struct": name_struct,
            }
        )

    description_struct = (
        hotel.get("description_struct")
        if isinstance(hotel.get("description_struct"), (list, dict))
        else None
    )
    description = _description_from_struct(description_struct)
    if not description:
        description = localized_string(hotel.get("description"))

    lat = hotel.get("latitude", hotel.get("lat"))
    lng = hotel.get("longitude", hotel.get("lng"))

    facts = hotel.get("facts") if isinstance(hotel.get("facts"), dict) else None
    payment_methods = (
        hotel.get("payment_methods")
        if isinstance(hotel.get("payment_methods"), (list, dict))
        else None
    )
    serp_filters = (
        hotel.get("serp_filters") if isinstance(hotel.get("serp_filters"), list) else None
    )
    keys_pickup = (
        hotel.get("keys_pickup") if isinstance(hotel.get("keys_pickup"), dict) else None
    )
    star_certificate = (
        hotel.get("star_certificate")
        if isinstance(hotel.get("star_certificate"), dict)
        else None
    )
    giata_code = _clip(hotel.get("giata_code"), 50) or None
    is_closed = bool(hotel.get("is_closed")) if hotel.get("is_closed") is not None else False
    is_gender = hotel.get("is_gender_specification_required")
    is_gender_specification_required = (
        bool(is_gender) if is_gender is not None else None
    )
    # RateHawk legacy string id when present
    supplier_slug = _clip(hotel.get("id") if not isinstance(hotel.get("id"), (int, float)) else "", 255) or None

    content_payload = {
        "accommodation_type": kind or None,
        "hotel_chain": hotel_chain or None,
        "giata_code": giata_code,
        "is_closed": is_closed,
        "is_gender_specification_required": is_gender_specification_required,
        "description_struct": description_struct,
        "facts": facts,
        "keys_pickup": keys_pickup,
        "star_certificate": star_certificate,
        "payment_methods": payment_methods,
        "serp_filters": serp_filters,
        "supplier_slug": supplier_slug,
        "images_ext": hotel_image_entries,
        "amenity_entries": amenity_entries,
    }

    staging = {
        "supplier_hotel_code": hid,
        "dedupe_key": compute_unique_key(name, star, resolved_region_id or "0"),
        "region_id": resolved_region_id or None,
        "code": _clip(f"RH{hid}", 30),
        "name": name,
        "star_rating": star,
        "description": description,
        "address_line1": _clip(line1, 255),
        "address_line2": _clip(line2, 255),
        "postal_code": _clip(hotel.get("postal_code"), 30),
        "location": _clip(address, 255),
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lng) if lng is not None else None,
        "phone": _clip(hotel.get("phone"), 255),
        "email": _clip(hotel.get("email"), 255),
        "image": _clip(image_urls[0] if image_urls else "", 2048),
        "amenity_names": amenity_names,
        "image_urls": image_urls,
        "room_payload": room_payload,
        "policy_payload": {
            "policy_struct": hotel.get("policy_struct")
            if isinstance(hotel.get("policy_struct"), list)
            else [],
            "metapolicy_struct": hotel.get("metapolicy_struct")
            if isinstance(hotel.get("metapolicy_struct"), dict)
            else {},
            "metapolicy_extra_info": localized_string(hotel.get("metapolicy_extra_info")),
            "facts": facts,
            "payment_methods": payment_methods,
            "serp_filters": serp_filters,
        },
        "accommodation_type": kind or None,
        "hotel_chain": hotel_chain or None,
        "check_in_time": check_in,
        "check_in_time_end": check_in_end,
        "check_out_time": check_out,
        "front_desk_time_start": fd_start,
        "front_desk_time_end": fd_end,
        "content_payload": content_payload,
    }
    return {"staging": staging, "rooms": rooms}


def staging_to_blender(staging: dict[str, Any]) -> dict[str, Any]:
    content = staging.get("content_payload") if isinstance(staging.get("content_payload"), dict) else {}
    amenity_entries = content.get("amenity_entries")
    if isinstance(amenity_entries, list) and amenity_entries:
        amenities = [
            {
                "name": str(a.get("name") or ""),
                "category": str(a.get("category") or "General"),
                "is_paid": bool(a.get("is_paid")),
                "image": None,
            }
            for a in amenity_entries
            if isinstance(a, dict) and a.get("name")
        ]
    else:
        amenities = [
            {"name": str(n), "category": "General", "is_paid": False, "image": None}
            for n in staging.get("amenity_names") or []
        ]

    images_ext = content.get("images_ext")
    if isinstance(images_ext, list) and images_ext:
        images = [
            {
                "url": resolve_ratehawk_image_url(str(img.get("url") or "")),
                "caption": "",
                "category_slug": str(img.get("category_slug") or ""),
            }
            for img in images_ext
            if isinstance(img, dict) and img.get("url")
        ]
    else:
        images = [
            {"url": resolve_ratehawk_image_url(str(url)), "caption": "", "category_slug": ""}
            for url in (staging.get("image_urls") or [])
        ]

    line1 = staging.get("address_line1") or ""
    line2 = staging.get("address_line2") or ""
    policy = staging.get("policy_payload") if isinstance(staging.get("policy_payload"), dict) else {}

    check_in = staging.get("check_in_time") or content.get("check_in_time")
    check_out = staging.get("check_out_time") or content.get("check_out_time")

    return {
        "HotelCode": staging["supplier_hotel_code"],
        "name": staging["name"],
        "star": staging["star_rating"],
        "address": f"{line1} {line2}".strip(),
        "geoPoint": {"lat": staging.get("latitude"), "lng": staging.get("longitude")},
        "location": staging.get("location") or "",
        "hotelPhone": staging.get("phone") or "",
        "zipCode": staging.get("postal_code") or "",
        "email": staging.get("email") or "",
        "allamenities": amenities,
        "image": resolve_ratehawk_image_url(str(staging.get("image") or "")),
        "images": images,
        "description": staging.get("description") or "",
        "room_groups": staging.get("room_payload") or [],
        "policy_struct": policy.get("policy_struct") or [],
        "metapolicy_struct": policy.get("metapolicy_struct") or {},
        "metapolicy_extra_info": policy.get("metapolicy_extra_info") or "",
        "facts": policy.get("facts") or content.get("facts"),
        "payment_methods": policy.get("payment_methods") or content.get("payment_methods"),
        "serp_filters": policy.get("serp_filters") or content.get("serp_filters"),
        "checkIn": check_in or "14:00:00",
        "checkOut": check_out or "12:00:00",
        "check_in_time_end": staging.get("check_in_time_end"),
        "front_desk_time_start": staging.get("front_desk_time_start"),
        "front_desk_time_end": staging.get("front_desk_time_end"),
        "accommodation_type": staging.get("accommodation_type") or content.get("accommodation_type"),
        "hotel_chain": staging.get("hotel_chain") or content.get("hotel_chain"),
        "giata_code": content.get("giata_code"),
        "is_closed": content.get("is_closed"),
        "is_gender_specification_required": content.get("is_gender_specification_required"),
        "description_struct": content.get("description_struct"),
        "keys_pickup": content.get("keys_pickup"),
        "star_certificate": content.get("star_certificate"),
        "supplier_slug": content.get("supplier_slug"),
        "_booking_source": "ratehawk",
    }


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
