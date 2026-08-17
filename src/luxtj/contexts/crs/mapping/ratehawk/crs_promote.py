"""CRS promote from staging — UUID-adapted port of Teenva crs_promote core path."""

from __future__ import annotations

import json
import random
import re
import secrets
import time
from typing import Any
from uuid import uuid4

from . import config, db
from .crs_normalize import flatten_hotel_content, flatten_room_group
from .crs_policies import build_hotel_policies_html, build_policy_text
from .parser import (
    compute_unique_key,
    normalize_name,
    normalize_star_rating,
    resolve_ratehawk_image_url,
    split_address,
    staging_to_blender,
)

_AMENITY_MASTER_LOCK_KEY = 87201401
_DEADLOCK_RETRY_ATTEMPTS = 6
_STALE_CLAIM_SECONDS = 120


def _clip(value: Any, limit: int) -> str:
    text = str(value or "")
    return text[:limit] if len(text) > limit else text


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:100] or "amenity"


def generate_hotel_code() -> str:
    return secrets.token_hex(8)[:12].upper()


def _retry_on_deadlock(fn, *, label: str = "promote"):
    last: BaseException | None = None
    for attempt in range(_DEADLOCK_RETRY_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:
            last = exc
            msg = str(exc).lower()
            retryable = "deadlock" in msg or "unique" in msg
            if not retryable or attempt >= _DEADLOCK_RETRY_ATTEMPTS - 1:
                raise
            delay = 0.05 * (2**attempt) + random.uniform(0, 0.08)
            print(f"[crs_promote] retry {attempt + 1} {label}: {exc} sleep={delay:.2f}", flush=True)
            time.sleep(delay)
    raise last  # type: ignore[misc]


def staging_row_to_blender(row: dict[str, Any]) -> dict[str, Any]:
    amenity_names = row.get("amenity_names") or []
    if isinstance(amenity_names, str):
        amenity_names = json.loads(amenity_names)
    image_urls = row.get("image_urls") or []
    if isinstance(image_urls, str):
        image_urls = json.loads(image_urls)
    room_payload = row.get("room_payload") or []
    if isinstance(room_payload, str):
        room_payload = json.loads(room_payload)
    policy_payload = row.get("policy_payload") or {}
    if isinstance(policy_payload, str):
        policy_payload = json.loads(policy_payload)
    content_payload = row.get("content_payload") or {}
    if isinstance(content_payload, str):
        content_payload = json.loads(content_payload)
    staging = {
        "supplier_hotel_code": row["supplier_hotel_code"],
        "name": row["name"],
        "star_rating": float(row.get("star_rating") or 0),
        "description": row.get("description") or "",
        "address_line1": row.get("address_line1") or "",
        "address_line2": row.get("address_line2") or "",
        "postal_code": row.get("postal_code") or "",
        "location": row.get("location") or "",
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "phone": row.get("phone") or "",
        "email": row.get("email") or "",
        "image": row.get("image") or "",
        "amenity_names": amenity_names,
        "image_urls": image_urls,
        "room_payload": room_payload,
        "policy_payload": policy_payload,
        "accommodation_type": row.get("accommodation_type"),
        "hotel_chain": row.get("hotel_chain"),
        "check_in_time": row.get("check_in_time"),
        "check_in_time_end": row.get("check_in_time_end"),
        "check_out_time": row.get("check_out_time"),
        "front_desk_time_start": row.get("front_desk_time_start"),
        "front_desk_time_end": row.get("front_desk_time_end"),
        "content_payload": content_payload if isinstance(content_payload, dict) else {},
    }
    return staging_to_blender(staging)


def _hotel_scalar_content(hotel: dict[str, Any]) -> dict[str, Any]:
    """Flat nullable hotel content columns (supplier-agnostic)."""
    flat = flatten_hotel_content(hotel)
    is_closed = hotel.get("is_closed")
    is_gender = hotel.get("is_gender_specification_required")
    return {
        "accommodation_type": _clip(hotel.get("accommodation_type"), 100) or None,
        "hotel_chain": _clip(hotel.get("hotel_chain"), 255) or None,
        "check_in_time_end": _clip(hotel.get("check_in_time_end"), 20) or None,
        "giata_code": _clip(hotel.get("giata_code"), 50) or None,
        "is_closed": bool(is_closed) if is_closed is not None else None,
        "is_gender_specification_required": bool(is_gender) if is_gender is not None else None,
        "supplier_slug": _clip(hotel.get("supplier_slug"), 255) or None,
        "floors_count": flat["floors_count"],
        "rooms_count": flat["rooms_count"],
        "year_built": flat["year_built"],
        "year_renovated": flat["year_renovated"],
        "electricity_frequency": flat["electricity_frequency"],
        "electricity_voltage": flat["electricity_voltage"],
        "electricity_sockets": flat["electricity_sockets"],
        "star_certificate_id": flat["star_certificate_id"],
        "star_certificate_valid_to": flat["star_certificate_valid_to"],
        "keys_pickup_type": flat["keys_pickup_type"],
        "keys_pickup_phone": flat["keys_pickup_phone"],
        "keys_pickup_email": flat["keys_pickup_email"],
        "keys_pickup_is_contactless": flat["keys_pickup_is_contactless"],
        "keys_pickup_address": flat["keys_pickup_address"],
        "keys_pickup_extra_info": flat["keys_pickup_extra_info"],
        "register_record": flat["register_record"],
        "register_link": flat["register_link"],
        "register_email": flat["register_email"],
        "register_phone": flat["register_phone"],
        "register_status": flat["register_status"],
        "register_kind": flat["register_kind"],
        "register_name": flat["register_name"],
        "register_address": flat["register_address"],
        "register_status_end_date": flat["register_status_end_date"],
        "register_taxpayer_number": flat["register_taxpayer_number"],
        "register_state_registration_number": flat["register_state_registration_number"],
        "register_work_time": flat["register_work_time"],
        "external_code": flat["external_code"],
        "_children": flat,
    }


def _sync_hotel_content_children(cur: Any, hotel_id: str, hotel: dict[str, Any], now) -> None:
    """Replace description / payment / tags / policy / register child rows."""
    flat = flatten_hotel_content(hotel)

    # description sections
    cur.execute(
        "DELETE FROM hotel_crs_hotel_description_sections WHERE hotel_id = %s",
        (hotel_id,),
    )
    for section in flat["description_sections"]:
        cur.execute(
            """
            INSERT INTO hotel_crs_hotel_description_sections (
                id, hotel_id, title, body, sort_order, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                hotel_id,
                section["title"],
                section["body"],
                section["sort_order"],
                now,
                now,
            ),
        )

    cur.execute(
        "DELETE FROM hotel_crs_hotel_payment_methods WHERE hotel_id = %s",
        (hotel_id,),
    )
    for method in flat["payment_methods"]:
        cur.execute(
            """
            INSERT INTO hotel_crs_hotel_payment_methods (
                id, hotel_id, method_code, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hotel_id, method_code) DO NOTHING
            """,
            (str(uuid4()), hotel_id, method, now, now),
        )

    cur.execute(
        "DELETE FROM hotel_crs_hotel_feature_tags WHERE hotel_id = %s",
        (hotel_id,),
    )
    for tag in flat["feature_tags"]:
        cur.execute(
            """
            INSERT INTO hotel_crs_hotel_feature_tags (
                id, hotel_id, tag, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hotel_id, tag) DO NOTHING
            """,
            (str(uuid4()), hotel_id, tag, now, now),
        )

    # policy sections
    cur.execute(
        """
        DELETE FROM hotel_crs_hotel_policy_item_attrs
        WHERE policy_item_id IN (
            SELECT id FROM hotel_crs_hotel_policy_items WHERE hotel_id = %s
        )
        """,
        (hotel_id,),
    )
    cur.execute("DELETE FROM hotel_crs_hotel_policy_items WHERE hotel_id = %s", (hotel_id,))
    cur.execute(
        "DELETE FROM hotel_crs_hotel_policy_sections WHERE hotel_id = %s",
        (hotel_id,),
    )
    for section in flat["policy_sections"]:
        cur.execute(
            """
            INSERT INTO hotel_crs_hotel_policy_sections (
                id, hotel_id, section_type, title, body, sort_order, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                hotel_id,
                section["section_type"],
                section["title"],
                section["body"],
                section["sort_order"],
                now,
                now,
            ),
        )
    for item in flat["policy_items"]:
        item_id = str(uuid4())
        cur.execute(
            """
            INSERT INTO hotel_crs_hotel_policy_items (
                id, hotel_id, category, sort_order, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (item_id, hotel_id, item["category"], item["sort_order"], now, now),
        )
        for key, value in (item.get("attrs") or {}).items():
            cur.execute(
                """
                INSERT INTO hotel_crs_hotel_policy_item_attrs (
                    id, policy_item_id, attr_key, attr_value, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_item_id, attr_key) DO NOTHING
                """,
                (
                    str(uuid4()),
                    item_id,
                    str(key)[:80],
                    str(value) if value is not None else None,
                    now,
                    now,
                ),
            )

    cur.execute(
        "DELETE FROM hotel_crs_hotel_register_room_categories WHERE hotel_id = %s",
        (hotel_id,),
    )
    for row in flat["register_rooms"]:
        cur.execute(
            """
            INSERT INTO hotel_crs_hotel_register_room_categories (
                id, hotel_id, category_type, rooms_count, sort_order, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                hotel_id,
                row["category_type"],
                row["rooms_count"],
                row["sort_order"],
                now,
                now,
            ),
        )


def _get_or_create_supplier(cur: Any, booking_source_id: str) -> str:
    cur.execute(
        """
        SELECT id FROM hotel_crs_suppliers
        WHERE booking_source_id = %s AND supplier_type = 'API'
        LIMIT 1
        """,
        (booking_source_id,),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])
    supplier_id = str(uuid4())
    now = db._utc_now()
    cur.execute(
        """
        INSERT INTO hotel_crs_suppliers (
            id, booking_source_id, supplier_type, user_id, created_at, updated_at
        ) VALUES (%s, %s, 'API', NULL, %s, %s)
        ON CONFLICT (booking_source_id, supplier_type) DO NOTHING
        """,
        (supplier_id, booking_source_id, now, now),
    )
    cur.execute(
        """
        SELECT id FROM hotel_crs_suppliers
        WHERE booking_source_id = %s AND supplier_type = 'API'
        LIMIT 1
        """,
        (booking_source_id,),
    )
    return str(cur.fetchone()[0])


def _ensure_amenities(cur: Any, names: list[str]) -> dict[str, str]:
    """Upsert amenity master rows.

    Uses a transaction-scoped advisory lock so a killed worker cannot leak a
    session lock and block all later room/hotel promotes.
    """
    result: dict[str, str] = {}
    if not names:
        return result
    # Held only until the surrounding transaction commits/rollbacks.
    cur.execute("SELECT pg_advisory_xact_lock(%s)", (_AMENITY_MASTER_LOCK_KEY,))
    now = db._utc_now()
    for name in names:
        label = str(name).strip()
        if not label:
            continue
        slug = _slugify(label)
        cur.execute(
            "SELECT id FROM hotel_crs_amenities WHERE slug = %s LIMIT 1",
            (slug,),
        )
        found = cur.fetchone()
        if found:
            result[label] = str(found[0])
            continue
        amenity_id = str(uuid4())
        cur.execute(
            """
            INSERT INTO hotel_crs_amenities (id, slug, name, category, scope, created_at, updated_at)
            VALUES (%s, %s, %s, NULL, 'both', %s, %s)
            ON CONFLICT (slug) DO NOTHING
            """,
            (amenity_id, slug, _clip(label, 255), now, now),
        )
        cur.execute("SELECT id FROM hotel_crs_amenities WHERE slug = %s LIMIT 1", (slug,))
        found = cur.fetchone()
        if found:
            result[label] = str(found[0])
    return result


def deduplicate_and_insert(
    hotels: list[dict[str, Any]],
    region_id: str,
    booking_source_id: str,
    *,
    sync_rooms: bool = True,
) -> dict[str, int]:
    stats = {
        "inserted": 0,
        "existing": 0,
        "errors": 0,
        "hotelImagesSynced": 0,
        "hotelAmenitiesMapped": 0,
        "roomGroupsSynced": 0,
        "roomImagesSynced": 0,
        "roomAmenitiesMapped": 0,
    }
    if not hotels or not region_id:
        return stats

    with db.db_cursor() as (_, cur):
        supplier_id = _get_or_create_supplier(cur, booking_source_id)
        hotel_data_map: dict[str, dict[str, Any]] = {}

        for hotel in hotels:
            name = str(hotel.get("name") or "")
            star = normalize_star_rating(hotel.get("star") or 0)
            if not name:
                stats["errors"] += 1
                continue
            unique_key = compute_unique_key(name, star, region_id)
            hotel_data_map[unique_key] = {
                "hotel": hotel,
                "supplier_id": supplier_id,
                "hotel_code": str(hotel.get("HotelCode") or ""),
                "name": name,
                "name_normalized": normalize_name(name),
                "star": int(star) if float(star) == int(star) else int(star),
                "star_float": star,
                "unique_key": unique_key,
            }

        if not hotel_data_map:
            return stats

        keys = list(hotel_data_map.keys())
        existing_key_map: dict[str, str] = {}
        for i in range(0, len(keys), 500):
            chunk = keys[i : i + 500]
            ph = ",".join(["%s"] * len(chunk))
            cur.execute(
                f"SELECT id, unique_key FROM hotel_crs_hotels WHERE unique_key IN ({ph})",
                tuple(chunk),
            )
            for hid, uk in cur.fetchall():
                existing_key_map[str(uk)] = str(hid)

        now = db._utc_now()
        unique_key_to_id: dict[str, str] = {}

        def _content_params(hotel: dict[str, Any], content: dict[str, Any]) -> tuple[Any, ...]:
            return (
                content["accommodation_type"],
                content["hotel_chain"],
                content["giata_code"],
                content["is_closed"],
                content["is_gender_specification_required"],
                content["floors_count"],
                content["rooms_count"],
                content["year_built"],
                content["year_renovated"],
                content["electricity_frequency"],
                content["electricity_voltage"],
                content["electricity_sockets"],
                content["star_certificate_id"],
                content["star_certificate_valid_to"],
                content["keys_pickup_type"],
                content["keys_pickup_phone"],
                content["keys_pickup_email"],
                content["keys_pickup_is_contactless"],
                content["keys_pickup_address"],
                content["keys_pickup_extra_info"],
                content["register_record"],
                content["register_link"],
                content["register_email"],
                content["register_phone"],
                content["register_status"],
                content["register_kind"],
                content["register_name"],
                content["register_address"],
                content["register_status_end_date"],
                content["register_taxpayer_number"],
                content["register_state_registration_number"],
                content["register_work_time"],
                content["supplier_slug"],
                content["external_code"],
            )

        for uk, data in hotel_data_map.items():
            hotel = data["hotel"]
            content = _hotel_scalar_content(hotel)
            if uk in existing_key_map:
                hotel_id = existing_key_map[uk]
                unique_key_to_id[uk] = hotel_id
                stats["existing"] += 1
                image = resolve_ratehawk_image_url(str(hotel.get("image") or ""))
                cur.execute(
                    """
                    UPDATE hotel_crs_hotels SET
                        email = %s,
                        check_in_time = %s,
                        check_in_time_end = %s,
                        check_out_time = %s,
                        front_desk_time_start = %s,
                        front_desk_time_end = %s,
                        description = %s,
                        policy_text = %s,
                        hotel_policies = %s,
                        image = COALESCE(NULLIF(%s, ''), image),
                        accommodation_type = %s,
                        hotel_chain = %s,
                        giata_code = %s,
                        is_closed = %s,
                        is_gender_specification_required = %s,
                        floors_count = %s,
                        rooms_count = %s,
                        year_built = %s,
                        year_renovated = %s,
                        electricity_frequency = %s,
                        electricity_voltage = %s,
                        electricity_sockets = %s,
                        star_certificate_id = %s,
                        star_certificate_valid_to = %s,
                        keys_pickup_type = %s,
                        keys_pickup_phone = %s,
                        keys_pickup_email = %s,
                        keys_pickup_is_contactless = %s,
                        keys_pickup_address = %s,
                        keys_pickup_extra_info = %s,
                        register_record = %s,
                        register_link = %s,
                        register_email = %s,
                        register_phone = %s,
                        register_status = %s,
                        register_kind = %s,
                        register_name = %s,
                        register_address = %s,
                        register_status_end_date = %s,
                        register_taxpayer_number = %s,
                        register_state_registration_number = %s,
                        register_work_time = %s,
                        supplier_slug = %s,
                        external_code = %s,
                        status = CASE WHEN %s THEN FALSE ELSE status END,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        _clip(hotel.get("email"), 255),
                        _clip(hotel.get("checkIn") or "14:00:00", 20),
                        content["check_in_time_end"],
                        _clip(hotel.get("checkOut") or "12:00:00", 20),
                        _clip(hotel.get("front_desk_time_start"), 20) or None,
                        _clip(hotel.get("front_desk_time_end"), 20) or None,
                        str(hotel.get("description") or ""),
                        build_policy_text(hotel),
                        build_hotel_policies_html(hotel),
                        _clip(image, 2048) or "",
                        *_content_params(hotel, content),
                        bool(content["is_closed"]),
                        now,
                        hotel_id,
                    ),
                )
                continue
            hotel_id = str(uuid4())
            line1, line2 = split_address(str(hotel.get("address") or ""))
            geo = hotel.get("geoPoint") if isinstance(hotel.get("geoPoint"), dict) else {}
            image = resolve_ratehawk_image_url(str(hotel.get("image") or ""))
            cur.execute(
                """
                INSERT INTO hotel_crs_hotels (
                    id, code, name, name_normalized, star_rating, unique_key,
                    region_id, address_line1, address_line2, postal_code, location,
                    latitude, longitude, phone, email, check_in_time, check_in_time_end,
                    check_out_time, front_desk_time_start, front_desk_time_end, description,
                    policy_text, hotel_policies, image,
                    accommodation_type, hotel_chain, giata_code, is_closed,
                    is_gender_specification_required,
                    floors_count, rooms_count, year_built, year_renovated,
                    electricity_frequency, electricity_voltage, electricity_sockets,
                    star_certificate_id, star_certificate_valid_to,
                    keys_pickup_type, keys_pickup_phone, keys_pickup_email,
                    keys_pickup_is_contactless, keys_pickup_address, keys_pickup_extra_info,
                    register_record, register_link, register_email, register_phone,
                    register_status, register_kind, register_name, register_address,
                    register_status_end_date, register_taxpayer_number,
                    register_state_registration_number, register_work_time,
                    supplier_slug, external_code, status, created_at, updated_at
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s
                )
                ON CONFLICT (unique_key) DO NOTHING
                """,
                (
                    hotel_id,
                    generate_hotel_code(),
                    _clip(data["name"], 255),
                    _clip(data["name_normalized"], 255),
                    int(data["star_float"]),
                    uk,
                    region_id,
                    _clip(line1, 255),
                    _clip(line2, 255),
                    _clip(hotel.get("zipCode"), 30),
                    _clip(hotel.get("location"), 255),
                    geo.get("lat"),
                    geo.get("lng"),
                    _clip(hotel.get("hotelPhone"), 255),
                    _clip(hotel.get("email"), 255),
                    _clip(hotel.get("checkIn") or "14:00:00", 20),
                    content["check_in_time_end"],
                    _clip(hotel.get("checkOut") or "12:00:00", 20),
                    _clip(hotel.get("front_desk_time_start"), 20) or None,
                    _clip(hotel.get("front_desk_time_end"), 20) or None,
                    str(hotel.get("description") or ""),
                    build_policy_text(hotel),
                    build_hotel_policies_html(hotel),
                    _clip(image, 2048),
                    *_content_params(hotel, content),
                    False if content["is_closed"] else True,
                    now,
                    now,
                ),
            )
            if cur.rowcount:
                unique_key_to_id[uk] = hotel_id
                stats["inserted"] += 1
            else:
                cur.execute(
                    "SELECT id FROM hotel_crs_hotels WHERE unique_key = %s",
                    (uk,),
                )
                found = cur.fetchone()
                if found:
                    unique_key_to_id[uk] = str(found[0])
                    stats["existing"] += 1

        # Supplier maps
        for uk, data in hotel_data_map.items():
            hotel_id = unique_key_to_id.get(uk)
            code = data["hotel_code"]
            if not hotel_id or not code:
                continue
            cur.execute(
                """
                INSERT INTO hotel_crs_supplier_hotel_map (
                    id, supplier_id, supplier_hotel_code, hotel_id, meta, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, NULL, %s, %s)
                ON CONFLICT (supplier_id, supplier_hotel_code, hotel_id) DO NOTHING
                """,
                (str(uuid4()), data["supplier_id"], code, hotel_id, now, now),
            )

        # Extended content
        all_amenity_names: list[str] = []
        for data in hotel_data_map.values():
            for a in data["hotel"].get("allamenities") or []:
                if isinstance(a, dict) and a.get("name"):
                    all_amenity_names.append(str(a["name"]))
        amenity_map = _ensure_amenities(cur, all_amenity_names)

        for uk, data in hotel_data_map.items():
            hotel_id = unique_key_to_id.get(uk)
            if not hotel_id:
                continue
            hotel = data["hotel"]
            # Replace hotel images/amenities so re-promote stays idempotent.
            cur.execute("DELETE FROM hotel_crs_hotel_images WHERE hotel_id = %s", (hotel_id,))
            cur.execute(
                "DELETE FROM hotel_crs_hotel_amenity_map WHERE hotel_id = %s",
                (hotel_id,),
            )
            _sync_hotel_content_children(cur, hotel_id, hotel, now)

            images = hotel.get("images") if isinstance(hotel.get("images"), list) else []
            for idx, img in enumerate(images[:50]):
                url = ""
                category = None
                if isinstance(img, dict):
                    url = resolve_ratehawk_image_url(str(img.get("url") or ""))
                    category = _clip(img.get("category_slug"), 100) or None
                elif isinstance(img, str):
                    url = resolve_ratehawk_image_url(img)
                if not url:
                    continue
                cur.execute(
                    """
                    INSERT INTO hotel_crs_hotel_images (
                        id, hotel_id, url, caption, category_slug, sort_order, created_at, updated_at
                    ) VALUES (%s, %s, %s, NULL, %s, %s, %s, %s)
                    """,
                    (str(uuid4()), hotel_id, _clip(url, 2048), category, idx, now, now),
                )
                stats["hotelImagesSynced"] += 1

            for a in hotel.get("allamenities") or []:
                if not isinstance(a, dict):
                    continue
                label = str(a.get("name") or "")
                amenity_id = amenity_map.get(label)
                if not amenity_id:
                    continue
                cur.execute(
                    """
                    INSERT INTO hotel_crs_hotel_amenity_map (
                        id, hotel_id, amenity_id, group_name, is_paid, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (hotel_id, amenity_id, group_name) DO NOTHING
                    """,
                    (
                        str(uuid4()),
                        hotel_id,
                        amenity_id,
                        _clip(a.get("category") or "General", 100),
                        bool(a.get("is_paid")),
                        now,
                        now,
                    ),
                )
                stats["hotelAmenitiesMapped"] += 1

            if sync_rooms:
                room_stats = _replace_rooms(cur, hotel_id, hotel.get("room_groups") or [], now)
                for k, v in room_stats.items():
                    stats[k] = stats.get(k, 0) + v

    return stats


def _replace_rooms(cur: Any, hotel_id: str, room_groups: list[Any], now) -> dict[str, int]:
    stats = {"roomGroupsSynced": 0, "roomImagesSynced": 0, "roomAmenitiesMapped": 0}
    cur.execute("SELECT id FROM hotel_crs_room_groups WHERE hotel_id = %s", (hotel_id,))
    old_ids = [str(r[0]) for r in cur.fetchall()]
    if old_ids:
        ph = ",".join(["%s"] * len(old_ids))
        cur.execute(
            f"DELETE FROM hotel_crs_room_amenity_map WHERE room_group_id IN ({ph})",
            tuple(old_ids),
        )
        cur.execute(
            f"DELETE FROM hotel_crs_room_images WHERE room_group_id IN ({ph})",
            tuple(old_ids),
        )
        cur.execute("DELETE FROM hotel_crs_room_groups WHERE hotel_id = %s", (hotel_id,))

    seen: set[str] = set()
    amenity_labels: list[str] = []
    for rg in room_groups:
        if not isinstance(rg, dict):
            continue
        for a in rg.get("room_amenities") or []:
            if isinstance(a, str) and a.strip():
                amenity_labels.append(a.strip())
            elif isinstance(a, dict) and a.get("name"):
                amenity_labels.append(str(a["name"]))
    amenity_map = _ensure_amenities(cur, amenity_labels)

    for rg in room_groups:
        if not isinstance(rg, dict):
            continue
        code = str(rg.get("room_group_id") or "")
        if not code or code in seen:
            continue
        seen.add(code)
        room_id = str(uuid4())
        name = _clip(rg.get("name") or code, 255)
        flat = flatten_room_group(rg)
        main_name = _clip(flat.get("main_name") or name, 255) or None
        cur.execute(
            """
            INSERT INTO hotel_crs_room_groups (
                id, hotel_id, supplier_room_code, name, main_name, description,
                bedding_type, bathroom_type, size, capacity, bedrooms, balcony,
                view_code, view_type, room_class, class_label, quality, quality_label,
                gender, is_family, is_club, floor_type,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (hotel_id, supplier_room_code) DO NOTHING
            """,
            (
                room_id,
                hotel_id,
                _clip(code, 100),
                name,
                main_name,
                flat.get("description"),
                flat.get("bedding_type"),
                flat.get("bathroom_type"),
                flat.get("size"),
                flat.get("capacity"),
                flat.get("bedrooms"),
                flat.get("balcony"),
                flat.get("view_code"),
                flat.get("view_type"),
                flat.get("room_class"),
                flat.get("class_label"),
                flat.get("quality"),
                flat.get("quality_label"),
                flat.get("gender"),
                flat.get("is_family"),
                flat.get("is_club"),
                flat.get("floor_type"),
                now,
                now,
            ),
        )
        if not cur.rowcount:
            continue
        stats["roomGroupsSynced"] += 1

        # Prefer merged images_ext entries (url + category); fall back to images[].
        images = rg.get("images_ext") if isinstance(rg.get("images_ext"), list) else None
        if not images:
            images = rg.get("images") if isinstance(rg.get("images"), list) else []
        for idx, item in enumerate(images[:30]):
            category = None
            if isinstance(item, dict):
                resolved = resolve_ratehawk_image_url(str(item.get("url") or ""))
                category = _clip(item.get("category_slug"), 100) or None
            else:
                resolved = resolve_ratehawk_image_url(str(item or ""))
            if not resolved:
                continue
            cur.execute(
                """
                INSERT INTO hotel_crs_room_images (
                    id, room_group_id, url, category_slug, sort_order, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (str(uuid4()), room_id, _clip(resolved, 2048), category, idx, now, now),
            )
            stats["roomImagesSynced"] += 1

        for a in rg.get("room_amenities") or []:
            label = a.strip() if isinstance(a, str) else str((a or {}).get("name") or "")
            amenity_id = amenity_map.get(label)
            if not amenity_id:
                continue
            cur.execute(
                """
                INSERT INTO hotel_crs_room_amenity_map (
                    id, room_group_id, amenity_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (room_group_id, amenity_id) DO NOTHING
                """,
                (str(uuid4()), room_id, amenity_id, now, now),
            )
            stats["roomAmenitiesMapped"] += 1
    return stats


def _claim_staging_hotels(cur: Any, run_id: str, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id, supplier_hotel_code, region_id, name, star_rating, description,
               address_line1, address_line2, postal_code, location,
               latitude, longitude, phone, email, image,
               amenity_names, image_urls, room_payload, policy_payload,
               accommodation_type, hotel_chain,
               check_in_time, check_in_time_end, check_out_time,
               front_desk_time_start, front_desk_time_end, content_payload
        FROM staging_hotels
        WHERE mapping_run_id = %s
          AND hotel_promoted_at IS NULL
          AND (
            promote_claimed_at IS NULL
            OR promote_claimed_at < NOW() - (%s || ' seconds')::interval
          )
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT %s
        """,
        (run_id, str(_STALE_CLAIM_SECONDS), limit),
    )
    cols = [d.name for d in cur.description]
    rows = [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    ph = ",".join(["%s"] * len(ids))
    cur.execute(
        f"UPDATE staging_hotels SET promote_claimed_at = NOW(), updated_at = NOW() WHERE id IN ({ph})",
        tuple(ids),
    )
    return rows


def _claim_staging_for_rooms(cur: Any, run_id: str, limit: int) -> list[dict[str, Any]]:
    """Claim hotels that are promoted but still need room/extras sync."""
    cur.execute(
        """
        SELECT id, supplier_hotel_code, region_id, name, star_rating, description,
               address_line1, address_line2, postal_code, location,
               latitude, longitude, phone, email, image,
               amenity_names, image_urls, room_payload, policy_payload,
               accommodation_type, hotel_chain,
               check_in_time, check_in_time_end, check_out_time,
               front_desk_time_start, front_desk_time_end, content_payload
        FROM staging_hotels
        WHERE mapping_run_id = %s
          AND hotel_promoted_at IS NOT NULL
          AND rooms_promoted_at IS NULL
          AND (
            extras_claimed_at IS NULL
            OR extras_claimed_at < NOW() - (%s || ' seconds')::interval
          )
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT %s
        """,
        (run_id, str(_STALE_CLAIM_SECONDS), limit),
    )
    cols = [d.name for d in cur.description]
    rows = [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    ph = ",".join(["%s"] * len(ids))
    cur.execute(
        f"UPDATE staging_hotels SET extras_claimed_at = NOW(), updated_at = NOW() WHERE id IN ({ph})",
        tuple(ids),
    )
    return rows


def count_unpromoted_hotels(run_id: str) -> int:
    with db.db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM staging_hotels
            WHERE mapping_run_id = %s AND hotel_promoted_at IS NULL
            """,
            (run_id,),
        )
        return int(cur.fetchone()[0] or 0)


def count_pending_room_hotels(run_id: str) -> int:
    with db.db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM staging_hotels
            WHERE mapping_run_id = %s
              AND hotel_promoted_at IS NOT NULL
              AND rooms_promoted_at IS NULL
            """,
            (run_id,),
        )
        return int(cur.fetchone()[0] or 0)


def count_hotels_promoted(run_id: str) -> int:
    with db.db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM staging_hotels
            WHERE mapping_run_id = %s AND hotel_promoted_at IS NOT NULL
            """,
            (run_id,),
        )
        return int(cur.fetchone()[0] or 0)


def count_rooms_promoted(run_id: str) -> int:
    with db.db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM staging_hotels
            WHERE mapping_run_id = %s AND rooms_promoted_at IS NOT NULL
            """,
            (run_id,),
        )
        return int(cur.fetchone()[0] or 0)


def promote_hotels_batch(
    run_id: str, booking_source_id: str, limit: int | None = None
) -> dict[str, int]:
    """Promote hotel rows only (rooms synced by parallel room workers)."""
    batch_size = limit or config.promote_batch_size()

    def _claim():
        with db.db_cursor() as (_, cur):
            return _claim_staging_hotels(cur, run_id, batch_size)

    rows = _retry_on_deadlock(_claim, label="claim-hotels")
    if not rows:
        return {"promoted": 0, "inserted": 0, "existing": 0}

    by_region: dict[str, list[dict[str, Any]]] = {}
    ids: list[str] = []
    for row in rows:
        region_id = str(row.get("region_id") or "")
        blender = staging_row_to_blender(row)
        blender["room_groups"] = []  # rooms handled separately
        by_region.setdefault(region_id, []).append(blender)
        ids.append(str(row["id"]))

    inserted = existing = 0

    def _crs_write():
        ins = ex = 0
        for region_id, hotels in by_region.items():
            if not region_id:
                continue
            stats = deduplicate_and_insert(hotels, region_id, booking_source_id, sync_rooms=False)
            ins += int(stats.get("inserted") or 0)
            ex += int(stats.get("existing") or 0)
        return ins, ex

    inserted, existing = _retry_on_deadlock(_crs_write, label=f"hotels run={run_id}")

    def _mark():
        with db.db_cursor() as (_, cur):
            ph = ",".join(["%s"] * len(ids))
            cur.execute(
                f"""
                UPDATE staging_hotels
                SET hotel_promoted_at = NOW(), updated_at = NOW()
                WHERE id IN ({ph})
                """,
                tuple(ids),
            )

    _retry_on_deadlock(_mark, label="mark-hotels")
    return {"promoted": len(ids), "inserted": inserted, "existing": existing}


def _room_groups_for_staging_row(
    cur: Any,
    *,
    run_id: str,
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    blender = staging_row_to_blender(row)
    room_groups = blender.get("room_groups") if isinstance(blender.get("room_groups"), list) else []
    supplier_code = str(row["supplier_hotel_code"])
    cur.execute(
        """
        SELECT room_group_id, name, main_name, description, amenity_slugs, image_urls,
               rg_ext, name_struct, images_ext
        FROM staging_rooms
        WHERE mapping_run_id = %s AND supplier_hotel_code = %s
        """,
        (run_id, supplier_code),
    )
    staged_rooms = cur.fetchall()
    if not staged_rooms:
        return [rg for rg in room_groups if isinstance(rg, dict)]

    by_code: dict[str, dict[str, Any]] = {}
    for rg in room_groups:
        if isinstance(rg, dict) and rg.get("room_group_id"):
            by_code[str(rg["room_group_id"])] = dict(rg)
    for (
        rg_id,
        name,
        main_name,
        desc,
        amenities,
        images,
        rg_ext,
        name_struct,
        images_ext,
    ) in staged_rooms:
        amenities_val = amenities
        images_val = images
        rg_ext_val = rg_ext
        name_struct_val = name_struct
        images_ext_val = images_ext
        if isinstance(amenities_val, str):
            amenities_val = json.loads(amenities_val)
        if isinstance(images_val, str):
            images_val = json.loads(images_val)
        if isinstance(rg_ext_val, str):
            rg_ext_val = json.loads(rg_ext_val)
        if isinstance(name_struct_val, str):
            name_struct_val = json.loads(name_struct_val)
        if isinstance(images_ext_val, str):
            images_ext_val = json.loads(images_ext_val)
        code = str(rg_id)
        existing = by_code.get(code) or {}
        by_code[code] = {
            **existing,
            "room_group_id": code,
            "name": name or existing.get("name") or code,
            "main_name": main_name or existing.get("main_name"),
            "description": desc or existing.get("description") or "",
            "room_amenities": amenities_val or existing.get("room_amenities") or [],
            "images": images_val or existing.get("images") or [],
            "images_ext": images_ext_val or existing.get("images_ext") or [],
            "rg_ext": rg_ext_val or existing.get("rg_ext"),
            "name_struct": name_struct_val or existing.get("name_struct"),
        }
    return list(by_code.values())


def promote_rooms_batch(
    run_id: str, booking_source_id: str, limit: int | None = None
) -> dict[str, int]:
    """Promote rooms/images/amenities for hotels already inserted into CRS.

    Commits one hotel at a time so amenity locks and deletes stay short-lived.
    """
    batch_size = limit or config.promote_batch_size()

    def _claim():
        with db.db_cursor() as (_, cur):
            return _claim_staging_for_rooms(cur, run_id, batch_size)

    rows = _retry_on_deadlock(_claim, label="claim-rooms")
    if not rows:
        return {"promoted": 0, "rooms_synced": 0}

    rooms_synced = 0
    promoted = 0

    # Resolve supplier once (short txn).
    def _supplier() -> str:
        with db.db_cursor() as (_, cur):
            return _get_or_create_supplier(cur, booking_source_id)

    supplier_id = _retry_on_deadlock(_supplier, label="rooms-supplier")

    for row in rows:
        staging_id = str(row["id"])
        supplier_code = str(row["supplier_hotel_code"])

        def _one_hotel(
            staging_id: str = staging_id,
            supplier_code: str = supplier_code,
            row: dict[str, Any] = row,
        ) -> int:
            with db.db_cursor() as (_, cur):
                cur.execute(
                    """
                    SELECT hotel_id FROM hotel_crs_supplier_hotel_map
                    WHERE supplier_id = %s AND supplier_hotel_code = %s
                    LIMIT 1
                    """,
                    (supplier_id, supplier_code),
                )
                map_row = cur.fetchone()
                synced = 0
                if map_row:
                    crs_hotel_id = str(map_row[0])
                    room_groups = _room_groups_for_staging_row(cur, run_id=run_id, row=row)
                    stats = _replace_rooms(cur, crs_hotel_id, room_groups, db._utc_now())
                    synced = int(stats.get("roomGroupsSynced") or 0)
                cur.execute(
                    """
                    UPDATE staging_hotels
                    SET rooms_promoted_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (staging_id,),
                )
                return synced

        try:
            rooms_synced += int(
                _retry_on_deadlock(_one_hotel, label=f"rooms hotel={supplier_code}")
            )
            promoted += 1
        except Exception:
            # Leave rooms_promoted_at NULL so another worker can retry after claim TTL.
            raise

    return {"promoted": promoted, "rooms_synced": rooms_synced}


def promote_hotels_once(run_id: str, booking_source_id: str) -> dict[str, Any]:
    stats = promote_hotels_batch(run_id, booking_source_id)
    return {
        "promoted": stats["promoted"],
        "inserted": stats["inserted"],
        "existing": stats.get("existing", 0),
    }


def promote_rooms_once(run_id: str, booking_source_id: str) -> dict[str, Any]:
    stats = promote_rooms_batch(run_id, booking_source_id)
    return {"promoted": stats["promoted"], "rooms_synced": stats["rooms_synced"]}


def promote_until_empty(run_id: str, booking_source_id: str) -> dict[str, int]:
    """Sequential fallback (finalize / recovery). Prefer parallel pipeline in stream_mapper."""
    totals = {"promoted": 0, "inserted": 0, "existing": 0, "rooms_synced": 0}
    while True:
        run = db.fetch_run(run_id)
        if db.is_cancelled(run):
            break
        stats = promote_hotels_batch(run_id, booking_source_id)
        if stats["promoted"] == 0:
            break
        for k in ("promoted", "inserted", "existing"):
            totals[k] += stats[k]
    while True:
        run = db.fetch_run(run_id)
        if db.is_cancelled(run):
            break
        stats = promote_rooms_batch(run_id, booking_source_id)
        if stats["promoted"] == 0:
            break
        totals["promoted"] += stats["promoted"]
        totals["rooms_synced"] += stats["rooms_synced"]
    return totals
