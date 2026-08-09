"""Hotel common helpers — mirrors TeenvaHotelCommon (tokens, normalize, RateHawk rate helpers)."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
    HotelCrsAmenityRow,
    HotelCrsHotelAmenityMapRow,
    HotelCrsHotelImageRow,
    HotelCrsHotelRow,
    HotelCrsRoomAmenityMapRow,
    HotelCrsRoomGroupRow,
    HotelCrsRoomImageRow,
    HotelCrsSupplierHotelMapRow,
    HotelCrsSupplierRow,
)
from luxtj.contexts.hotel.infrastructure.persistence.sqlalchemy_models import (
    HotelBookingCancellationPolicyRow,
    HotelBookingExtraFeeRow,
)
from luxtj.utils import timeutils


class HotelCommon:
    """Shared helpers for hotel providers (tokens, UUID, CRS enrich, RateHawk rate normalize)."""

    # ── Token helpers ──────────────────────────────────────────────────

    @staticmethod
    def encode_result_token(booking_source: str, token: str) -> str:
        payload = {
            "booking_source": booking_source,
            "token": token,
            "time": int(time.time()),
        }
        return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()

    @staticmethod
    def decode_result_token(encoded: str) -> dict[str, Any] | None:
        try:
            raw = base64.b64decode(encoded.encode()).decode()
            data = json.loads(raw)
            if isinstance(data, dict) and "booking_source" in data and "token" in data:
                return data
        except Exception:
            return None
        return None

    @staticmethod
    def encode_list_token(booking_source: str, data: dict[str, Any]) -> str:
        payload = {
            "booking_source": booking_source,
            "data": data,
            "time": int(time.time()),
        }
        return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()

    @staticmethod
    def decode_list_token(encoded: str) -> dict[str, Any] | None:
        try:
            raw = base64.b64decode(encoded.encode()).decode()
            data = json.loads(raw)
            if isinstance(data, dict) and "booking_source" in data and "data" in data:
                return data
        except Exception:
            return None
        return None

    @staticmethod
    def hotel_block_snapshot_cache_key(list_token: str) -> str:
        return "hotel:block_room_v1:" + hashlib.sha256(list_token.encode()).hexdigest()

    # ── UUID / reference helpers ───────────────────────────────────────

    @staticmethod
    def generate_uuid(prefix: str = "", random_length: int = 16) -> str:
        time_part = f"{time.time():.6f}".replace(".", "")
        random_part = secrets.token_hex(random_length)
        return f"{prefix}{time_part}{random_part}"

    @staticmethod
    def generate_app_reference() -> str:
        """Hotel app reference: HTL + compact uuid fragment."""
        return "HTL" + uuid.uuid4().hex[:16].upper()

    @staticmethod
    def generate_hotel_code() -> str:
        n = secrets.randbelow(999999) + 1
        return f"HTL{n:06d}{str(int(time.time()))[-4:]}"

    # ── Misc helpers ───────────────────────────────────────────────────

    @staticmethod
    def split_address(address: str) -> dict[str, str]:
        parts = [p.strip() for p in address.split(",") if p.strip()]
        return {
            "line1": ", ".join(parts[:2]),
            "line2": ", ".join(parts[2:]),
        }

    @staticmethod
    def normalize_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower().strip())

    @staticmethod
    def compute_unique_key(name: str, star: int, region_id: str | int) -> str:
        return hashlib.md5(
            f"{HotelCommon.normalize_name(name)}|{star}|{region_id}".encode()
        ).hexdigest()

    # ── CRS enrich (async) ─────────────────────────────────────────────

    @staticmethod
    async def get_search_static_details_by_supplier_hotel_codes(
        session: AsyncSession,
        supplier_hotel_codes: list[str],
        booking_api_id: str,
    ) -> dict[str, dict[str, Any]]:
        if not booking_api_id:
            return {}
        codes = list({str(c) for c in supplier_hotel_codes if c})
        if not codes:
            return {}

        stmt = (
            select(HotelCrsSupplierHotelMapRow, HotelCrsHotelRow)
            .join(HotelCrsHotelRow, HotelCrsHotelRow.id == HotelCrsSupplierHotelMapRow.hotel_id)
            .join(
                HotelCrsSupplierRow,
                HotelCrsSupplierRow.id == HotelCrsSupplierHotelMapRow.supplier_id,
            )
            .where(HotelCrsSupplierRow.booking_source_id == booking_api_id)
            .where(HotelCrsSupplierHotelMapRow.supplier_hotel_code.in_(codes))
            .where(HotelCrsHotelRow.status.is_(True))
        )
        rows = (await session.execute(stmt)).all()
        out: dict[str, dict[str, Any]] = {}
        hotel_ids: list[str] = []
        for map_row, hotel in rows:
            code = str(map_row.supplier_hotel_code)
            hotel_dict = _hotel_row_to_dict(hotel)
            out[code] = {"hotel": hotel_dict, "other_amenities": []}
            hotel_ids.append(hotel.id)
        hotel_ids = list({h for h in hotel_ids if h})

        if hotel_ids:
            amenity_stmt = (
                select(
                    HotelCrsHotelAmenityMapRow.hotel_id,
                    HotelCrsAmenityRow.name,
                    HotelCrsHotelAmenityMapRow.group_name,
                )
                .join(
                    HotelCrsAmenityRow,
                    HotelCrsAmenityRow.id == HotelCrsHotelAmenityMapRow.amenity_id,
                )
                .where(HotelCrsHotelAmenityMapRow.hotel_id.in_(hotel_ids))
                .order_by(HotelCrsAmenityRow.name)
            )
            by_hotel: dict[str, list[dict[str, Any]]] = {}
            for hid, name, group_name in (await session.execute(amenity_stmt)).all():
                cat = (group_name or "").strip() or "General"
                by_hotel.setdefault(str(hid), []).append(
                    {"name": str(name), "category": cat, "image": None}
                )
            for map_row, hotel in rows:
                code = str(map_row.supplier_hotel_code)
                if code in out:
                    out[code]["other_amenities"] = by_hotel.get(hotel.id, [])
        return out

    @staticmethod
    def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float | None:
        try:
            if not all(isinstance(x, (int, float)) for x in (lat1, lng1, lat2, lng2)):
                return None
            if abs(lat1) < 1e-9 and abs(lng1) < 1e-9:
                return None
            if abs(lat2) < 1e-9 and abs(lng2) < 1e-9:
                return None
            from math import asin, cos, radians, sin, sqrt

            r = 6371.0
            dlat = radians(lat2 - lat1)
            dlng = radians(lng2 - lng1)
            a = (
                sin(dlat / 2) ** 2
                + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
            )
            return round(2 * r * asin(sqrt(a)), 1)
        except Exception:
            return None

    @staticmethod
    async def get_hotel_crs_details_for_supplier_code(
        session: AsyncSession,
        supplier_hotel_code: str,
        booking_api_id: str,
    ) -> dict[str, Any] | None:
        if not booking_api_id or not supplier_hotel_code:
            return None
        stmt = (
            select(HotelCrsSupplierHotelMapRow, HotelCrsHotelRow)
            .join(HotelCrsHotelRow, HotelCrsHotelRow.id == HotelCrsSupplierHotelMapRow.hotel_id)
            .join(
                HotelCrsSupplierRow,
                HotelCrsSupplierRow.id == HotelCrsSupplierHotelMapRow.supplier_id,
            )
            .where(HotelCrsSupplierRow.booking_source_id == booking_api_id)
            .where(HotelCrsSupplierHotelMapRow.supplier_hotel_code == supplier_hotel_code)
            .where(HotelCrsHotelRow.status.is_(True))
        )
        row = (await session.execute(stmt)).first()
        if not row:
            return None
        _map_row, hotel = row
        hotel_dict = _hotel_row_to_dict(hotel)
        hotel_id = hotel.id

        gallery: list[str] = []
        img_stmt = (
            select(HotelCrsHotelImageRow.url)
            .where(HotelCrsHotelImageRow.hotel_id == hotel_id)
            .order_by(HotelCrsHotelImageRow.sort_order, HotelCrsHotelImageRow.id)
        )
        gallery = [str(u) for (u,) in (await session.execute(img_stmt)).all()]

        other_amenities: list[dict[str, Any]] = []
        am_stmt = (
            select(HotelCrsAmenityRow.name, HotelCrsHotelAmenityMapRow.group_name)
            .join(
                HotelCrsAmenityRow,
                HotelCrsAmenityRow.id == HotelCrsHotelAmenityMapRow.amenity_id,
            )
            .where(HotelCrsHotelAmenityMapRow.hotel_id == hotel_id)
            .order_by(HotelCrsAmenityRow.name)
        )
        for name, group_name in (await session.execute(am_stmt)).all():
            cat = (group_name or "").strip() or "General"
            other_amenities.append({"name": str(name), "category": cat, "image": None})

        return {
            "hotel": hotel_dict,
            "gallery_image_urls": gallery,
            "other_amenities": other_amenities,
        }

    @staticmethod
    async def get_crs_room_static_by_exact_room_names(
        session: AsyncSession,
        hotel_crs_id: str,
        room_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not hotel_crs_id:
            return {}
        names = list({str(n) for n in room_names if n})
        if not names:
            return {}
        groups = (
            await session.execute(
                select(
                    HotelCrsRoomGroupRow.id,
                    HotelCrsRoomGroupRow.name,
                    HotelCrsRoomGroupRow.supplier_room_code,
                ).where(
                    HotelCrsRoomGroupRow.hotel_id == hotel_crs_id,
                    HotelCrsRoomGroupRow.name.in_(names),
                )
            )
        ).all()
        id_by_name: dict[str, str] = {}
        code_by_name: dict[str, str] = {}
        for gid, name, room_code in groups:
            n = str(name)
            if n and n not in id_by_name:
                id_by_name[n] = str(gid)
                code_by_name[n] = str(room_code or "")
        group_ids = list(id_by_name.values())
        if not group_ids:
            return {}

        images_by_gid: dict[str, list[str]] = {}
        img_rows = (
            await session.execute(
                select(HotelCrsRoomImageRow.room_group_id, HotelCrsRoomImageRow.url)
                .where(HotelCrsRoomImageRow.room_group_id.in_(group_ids))
                .order_by(HotelCrsRoomImageRow.sort_order, HotelCrsRoomImageRow.id)
            )
        ).all()
        for gid, url in img_rows:
            u = str(url or "").strip()
            if u:
                images_by_gid.setdefault(str(gid), []).append(u)

        amenities_by_gid: dict[str, list[dict[str, Any]]] = {}
        am_rows = (
            await session.execute(
                select(
                    HotelCrsRoomAmenityMapRow.room_group_id,
                    HotelCrsAmenityRow.slug,
                    HotelCrsAmenityRow.name,
                )
                .join(
                    HotelCrsAmenityRow,
                    HotelCrsAmenityRow.id == HotelCrsRoomAmenityMapRow.amenity_id,
                )
                .where(HotelCrsRoomAmenityMapRow.room_group_id.in_(group_ids))
                .order_by(HotelCrsAmenityRow.slug)
            )
        ).all()
        for gid, slug, name in am_rows:
            label = (str(slug or "").strip() or str(name or "")).strip()
            if not label:
                continue
            amenities_by_gid.setdefault(str(gid), []).append(
                {"name": label, "image": None, "category": "ALL"}
            )

        return {
            room_name: {
                "images": images_by_gid.get(gid, []),
                "amenities": amenities_by_gid.get(gid, []),
                "supplier_room_code": code_by_name.get(room_name, ""),
            }
            for room_name, gid in id_by_name.items()
        }

    # ── RateHawk rate helpers ──────────────────────────────────────────

    @staticmethod
    def ratehawk_first_payment_type(rate: dict[str, Any]) -> dict[str, Any] | None:
        types = (rate.get("payment_options") or {}).get("payment_types") or []
        return types[0] if isinstance(types, list) and types else None

    @staticmethod
    def ratehawk_format_extra_fee_display_name(name: str) -> str:
        s = name.replace("_", " ").strip()
        return s.title() if s else name

    @staticmethod
    def ratehawk_parse_payment_tax_breakdown(
        pt: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if pt is None:
            return {"includedTaxesSum": 0.0, "vatIncludedAmount": 0.0, "extraFees": []}
        included_taxes = 0.0
        vat_included = 0.0
        extra_fees: list[dict[str, Any]] = []
        taxes = ((pt.get("tax_data") or {}).get("taxes")) or None
        if isinstance(taxes, list):
            for t in taxes:
                if not isinstance(t, dict):
                    continue
                amt = float(t.get("amount") or 0)
                name = str(t.get("name") or "tax")
                cc = str(t.get("currency_code") or "")
                if t.get("included_by_supplier"):
                    included_taxes += amt
                else:
                    extra_fees.append(
                        {
                            "name": HotelCommon.ratehawk_format_extra_fee_display_name(name),
                            "amount": round(amt, 2),
                            "currency_code": cc,
                        }
                    )
        vat = pt.get("vat_data")
        if isinstance(vat, dict) and vat.get("included"):
            vat_included = float(vat.get("amount") or 0)
        return {
            "includedTaxesSum": round(included_taxes, 2),
            "vatIncludedAmount": round(vat_included, 2),
            "extraFees": extra_fees,
        }

    @staticmethod
    def ratehawk_format_cancel_policy_instant(v: str | None) -> str | None:
        if not v:
            return None
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
        except Exception:
            return None

    @staticmethod
    def ratehawk_map_cancellation_policies(pt: dict[str, Any] | None) -> list[dict[str, Any]]:
        if pt is None:
            return []
        policies = ((pt.get("cancellation_penalties") or {}).get("policies")) or []
        if not isinstance(policies, list):
            return []
        out: list[dict[str, Any]] = []
        for p in policies:
            if not isinstance(p, dict):
                continue
            start_at = p.get("start_at")
            end_at = p.get("end_at")
            out.append(
                {
                    "from": HotelCommon.ratehawk_format_cancel_policy_instant(
                        start_at if isinstance(start_at, str) and start_at else None
                    ),
                    "to": HotelCommon.ratehawk_format_cancel_policy_instant(
                        end_at if isinstance(end_at, str) and end_at else None
                    ),
                    "amount": round(float(p.get("amount_show") or p.get("amount_charge") or 0), 2),
                }
            )
        return out

    @staticmethod
    def ratehawk_format_meal_display_name(meal_code: str) -> str:
        meal_code = meal_code.strip()
        if not meal_code or meal_code.lower() == "nomeal":
            return "Room Only"
        s = re.sub(r"\s+", " ", meal_code.replace("-", " ").strip())
        return s.title() if s else meal_code

    @staticmethod
    def ratehawk_free_cancellation_before_iso(pt: dict[str, Any] | None) -> str | None:
        if pt is None:
            return None
        fcb = ((pt.get("cancellation_penalties") or {}).get("free_cancellation_before"))
        if not isinstance(fcb, str) or not fcb:
            return None
        try:
            dt = datetime.fromisoformat(fcb.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            return fcb

    @staticmethod
    def ratehawk_guests_to_rooms_payload(guests: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for g in guests:
            if not isinstance(g, dict):
                continue
            children = g.get("children") if isinstance(g.get("children"), list) else []
            child_ages = [int(c) for c in children]
            out.append(
                {
                    "adultCount": int(g.get("adults") or 1),
                    "childCount": len(child_ages),
                    "childAges": child_ages,
                }
            )
        return out or [{"adultCount": 1, "childCount": 0, "childAges": []}]

    @staticmethod
    def ratehawk_normalize_hp_rate_row(rate: dict[str, Any]) -> dict[str, Any]:
        pt = HotelCommon.ratehawk_first_payment_type(rate)
        show_amount = float((pt or {}).get("show_amount") or 0)
        tax_breakdown = HotelCommon.ratehawk_parse_payment_tax_breakdown(pt)
        excluded_sum = sum(float(f.get("amount") or 0) for f in tax_breakdown["extraFees"])
        amount = round(show_amount + excluded_sum, 2)
        taxes_display = round(
            tax_breakdown["includedTaxesSum"] + tax_breakdown["vatIncludedAmount"], 2
        )
        meal_code = str(rate.get("meal") or "nomeal")
        meal_data = rate.get("meal_data") if isinstance(rate.get("meal_data"), dict) else {}
        breakfast_included = bool(meal_data.get("has_breakfast") or False)
        child_meal_included = breakfast_included and not bool(meal_data.get("no_child_meal") or False)
        meal_display = HotelCommon.ratehawk_format_meal_display_name(meal_code)
        return {
            "amount": amount,
            "taxes": taxes_display,
            "extraFees": tax_breakdown["extraFees"],
            "show_amount": round(show_amount, 2),
            "meal_code": meal_code,
            "meal_display": meal_display,
            "variation_label": meal_display,
            "breakfast_included": breakfast_included,
            "child_meal_included": child_meal_included,
            "free_cancellation_before": HotelCommon.ratehawk_free_cancellation_before_iso(pt),
            "cancel_policies": HotelCommon.ratehawk_map_cancellation_policies(pt),
            "available": int(rate.get("allotment") or 0),
            "book_hash": str(rate.get("book_hash") or ""),
            "room_name": str(rate.get("room_name") or ""),
        }

    @staticmethod
    def validate_rooms_for_search(rooms: list[Any]) -> str | None:
        """Return a user-facing error, or None if rooms are valid for PreSearch.

        Limits match RateHawk guest payload used in search (1–6 adults, 0–4 children
        aged 0–17 per room; at least one room; max 9 rooms).
        """
        if not isinstance(rooms, list) or not rooms:
            return "At least one room is required"
        if len(rooms) > 9:
            return "Maximum 9 rooms allowed"
        for i, room in enumerate(rooms):
            label = f"Room {i + 1}"
            if not isinstance(room, dict):
                return f"{label}: invalid room payload"
            try:
                adults = int(room.get("adultCount") or room.get("adult_count") or 0)
            except (TypeError, ValueError):
                return f"{label}: adultCount must be a number"
            if adults < 1 or adults > 6:
                return f"{label}: adultCount must be between 1 and 6"

            ages_raw = room.get("childAges") or room.get("child_ages")
            if ages_raw is None:
                ages_raw = []
            if not isinstance(ages_raw, list):
                return f"{label}: childAges must be a list"

            child_count_raw = room.get("childCount")
            if child_count_raw is None:
                child_count_raw = room.get("child_count")
            try:
                child_count = (
                    int(child_count_raw)
                    if child_count_raw is not None
                    else len(ages_raw)
                )
            except (TypeError, ValueError):
                return f"{label}: childCount must be a number"

            if child_count < 0 or child_count > 4:
                return f"{label}: childCount must be between 0 and 4"
            if child_count != len(ages_raw):
                return f"{label}: child ages are required (0–17) for each child"
            for age in ages_raw:
                try:
                    ai = int(age)
                except (TypeError, ValueError):
                    return f"{label}: each child age must be a number between 0 and 17"
                if ai < 0 or ai > 17:
                    return f"{label}: each child age must be between 0 and 17"
        return None

    @staticmethod
    def normalize_rooms_for_search(rooms: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for room in rooms:
            if not isinstance(room, dict):
                continue
            adults = max(1, min(6, int(room.get("adultCount") or room.get("adult_count") or 1)))
            ages_raw = room.get("childAges") or room.get("child_ages")
            child_ages: list[int] = []
            if isinstance(ages_raw, list):
                for a in ages_raw:
                    try:
                        ai = int(a)
                    except (TypeError, ValueError):
                        continue
                    if 0 <= ai <= 17:
                        child_ages.append(ai)
            if len(child_ages) > 4:
                child_ages = child_ages[:4]
            out.append(
                {
                    "adultCount": adults,
                    "childAges": child_ages,
                    "childCount": len(child_ages),
                }
            )
        return out[:9]

    @staticmethod
    def hotel_stay_nights(checkin_ymd: str, checkout_ymd: str) -> int:
        try:
            cin = datetime.strptime(checkin_ymd[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            cout = datetime.strptime(checkout_ymd[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if cout <= cin:
                return 1
            return max(1, int(round((cout - cin).total_seconds() / 86400)))
        except Exception:
            return 1

    @staticmethod
    def ratehawk_residency_from_nationality(search_data: dict[str, Any]) -> str:
        n = re.sub(
            r"[^A-Za-z]",
            "",
            str(search_data.get("nationality") or search_data.get("Nationality") or "US"),
        ).upper()
        if len(n) >= 2:
            return n[:2].lower()
        return "gb"

    @staticmethod
    def parse_policy_instant_for_db(raw: Any) -> datetime | None:
        if not isinstance(raw, str) or not raw:
            return None
        s = re.sub(r"\s+UTC$", "", raw.strip(), flags=re.I)
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    async def persist_itinerary_cancellation_policies_and_extra_fees(
        session: AsyncSession,
        app_reference: str,
        hotel_booking_itinerary_detail_id: str,
        room: dict[str, Any],
        conversion_to_admin: float,
        penalty_currency3: str,
    ) -> None:
        penalty_currency3 = (penalty_currency3 or "USD").upper()[:3] or "USD"
        now = timeutils.datetime_now()
        policies: list[Any] = []
        for k in ("cancelPolicies", "CancelPolicies", "CancellationPolicies"):
            if isinstance(room.get(k), list) and room[k]:
                policies = room[k]
                break
        for i, pol in enumerate(policies):
            if not isinstance(pol, dict):
                continue
            start = end = None
            amount_base = 0.0
            row_currency = penalty_currency3
            if "from" in pol or "to" in pol:
                start = HotelCommon.parse_policy_instant_for_db(pol.get("from"))
                end = HotelCommon.parse_policy_instant_for_db(pol.get("to"))
                amount_base = float(pol.get("amount") or 0)
            elif "PeriodStart" in pol or "PeriodEnd" in pol or "PenaltyAmount" in pol:
                start = HotelCommon.parse_policy_instant_for_db(pol.get("PeriodStart"))
                end = HotelCommon.parse_policy_instant_for_db(pol.get("PeriodEnd"))
                amount_base = float(pol.get("PenaltyAmount") or 0)
                pc = str(pol.get("PenaltyCurrency") or "").upper()[:3]
                if pc:
                    row_currency = pc
            else:
                continue
            session.add(
                HotelBookingCancellationPolicyRow(
                    id=str(uuid.uuid4()),
                    app_reference=app_reference,
                    hotel_booking_itinerary_detail_id=hotel_booking_itinerary_detail_id,
                    sort_order=int(i),
                    period_start_at=start,
                    period_end_at=end,
                    penalty_amount=round(amount_base * conversion_to_admin, 2),
                    penalty_currency=row_currency,
                    created_at=now,
                    updated_at=now,
                )
            )

        fees: list[Any] = []
        for k in ("extraFees", "ExtraFees"):
            if isinstance(room.get(k), list) and room[k]:
                fees = room[k]
                break
        for i, fee in enumerate(fees):
            if not isinstance(fee, dict):
                continue
            raw_name = str(fee.get("name") or fee.get("Name") or "")
            if not raw_name:
                continue
            amt = float(fee.get("amount") or fee.get("Amount") or 0)
            fc = str(fee.get("currency") or fee.get("Currency") or penalty_currency3).upper()[:3]
            if not fc:
                fc = penalty_currency3
            included = fee.get("IsIncluded", fee.get("is_included"))
            session.add(
                HotelBookingExtraFeeRow(
                    id=str(uuid.uuid4()),
                    app_reference=app_reference,
                    hotel_booking_itinerary_detail_id=hotel_booking_itinerary_detail_id,
                    sort_order=int(i),
                    fee_name=raw_name,
                    amount=round(amt * conversion_to_admin, 2),
                    currency=fc,
                    is_included=included if isinstance(included, bool) else None,
                    created_at=now,
                    updated_at=now,
                )
            )


def _hotel_row_to_dict(hotel: HotelCrsHotelRow) -> dict[str, Any]:
    return {
        "id": hotel.id,
        "code": hotel.code,
        "name": hotel.name,
        "name_normalized": hotel.name_normalized,
        "star_rating": hotel.star_rating,
        "unique_key": hotel.unique_key,
        "region_id": getattr(hotel, "region_id", None),
        "address_line1": hotel.address_line1,
        "address_line2": hotel.address_line2,
        "postal_code": hotel.postal_code,
        "location": hotel.location,
        "latitude": float(hotel.latitude) if hotel.latitude is not None else 0,
        "longitude": float(hotel.longitude) if hotel.longitude is not None else 0,
        "phone": hotel.phone,
        "email": hotel.email,
        "check_in_time": hotel.check_in_time,
        "check_out_time": hotel.check_out_time,
        "front_desk_time_start": hotel.front_desk_time_start,
        "front_desk_time_end": hotel.front_desk_time_end,
        "description": hotel.description,
        "policy_text": hotel.policy_text,
        "hotel_policies": hotel.hotel_policies,
        # HotelCrsHotelRow has no meta column (policies/amenities live in related tables).
        "meta": getattr(hotel, "meta", None),
        "image": hotel.image,
        "status": hotel.status,
        "accommodation_type": getattr(hotel, "accommodation_type", None),
        "accommodation_type_code": getattr(hotel, "accommodation_type_code", None),
        "hotel_chain": getattr(hotel, "hotel_chain", None),
        "rooms_count": getattr(hotel, "rooms_count", None),
        "floors_count": getattr(hotel, "floors_count", None),
    }
