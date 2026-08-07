"""CRS hotel sync — mirrors HotelCrsService (dedupe, insert, room sync)."""

from __future__ import annotations

import html
import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.crs.domain.enums import CrsSupplierTypeEnum
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
from luxtj.contexts.hotel.domain.common import HotelCommon
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


def _safe_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


class HotelCrsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def deduplicate_and_insert(
        self, hotels: list[dict[str, Any]], city_id: str
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
        if not hotels or not city_id:
            return stats
        try:
            booking_sources = list(
                {str(h.get("_booking_source") or "") for h in hotels if h.get("_booking_source")}
            )
            supplier_map = await self.batch_get_or_create_suppliers(booking_sources)

            hotel_data_map: dict[str, dict[str, Any]] = {}
            normalized_names_map: dict[str, list[str]] = {}

            for hotel in hotels:
                source = str(hotel.get("_booking_source") or "")
                supplier_id = supplier_map.get(source)
                if not supplier_id:
                    stats["errors"] += 1
                    continue
                hotel_code = str(hotel.get("HotelCode") or "")
                name = str(hotel.get("name") or hotel.get("HotelName") or "")
                star = int(hotel.get("star") or hotel.get("StarRating") or 0)
                if not name:
                    stats["errors"] += 1
                    continue
                unique_key = HotelCommon.compute_unique_key(name, star, city_id)
                name_normalized = HotelCommon.normalize_name(name)
                lookup_key = f"{name_normalized}|{star}"
                hotel_data_map[unique_key] = {
                    "hotel": hotel,
                    "supplier_id": supplier_id,
                    "hotel_code": hotel_code,
                    "name": name,
                    "name_normalized": name_normalized,
                    "star": star,
                    "unique_key": unique_key,
                }
                normalized_names_map.setdefault(lookup_key, []).append(unique_key)

            if not hotel_data_map:
                return stats

            existing_hotels = await self._batch_find_existing_hotels(
                city_id, list(normalized_names_map.keys())
            )
            existing_key_map: dict[str, str] = {}
            for existing in existing_hotels:
                existing_norm = HotelCommon.normalize_name(existing.name)
                existing_star = int(existing.star_rating)
                lk = f"{existing_norm}|{existing_star}"
                if lk in normalized_names_map:
                    for uk in normalized_names_map[lk]:
                        if uk not in existing_key_map:
                            computed = HotelCommon.compute_unique_key(
                                existing.name, existing_star, city_id
                            )
                            if computed == uk:
                                existing_key_map[uk] = existing.id

            to_insert_batch: dict[str, dict[str, Any]] = {}
            hotel_code_map: dict[str, dict[str, Any]] = {}
            unique_key_to_id: dict[str, str] = {}

            for unique_key, data in hotel_data_map.items():
                hotel = data["hotel"]
                existing_id = existing_key_map.get(unique_key)
                if existing_id:
                    stats["existing"] += 1
                    unique_key_to_id[unique_key] = existing_id
                else:
                    to_insert_batch[unique_key] = self._build_insert_row(
                        hotel, data, city_id, unique_key
                    )
                if data["hotel_code"]:
                    hotel_code_map[unique_key] = {
                        "supplier_id": data["supplier_id"],
                        "hotel_code": data["hotel_code"],
                        "crs_hotel_id": existing_id,
                    }

            if to_insert_batch:
                inserted_map = await self._batch_insert_hotels(
                    list(to_insert_batch.values()), city_id
                )
                stats["inserted"] += len(inserted_map)
                unique_key_to_id.update(inserted_map)

            for uk, hotel_id in unique_key_to_id.items():
                if uk in hotel_code_map:
                    hotel_code_map[uk]["crs_hotel_id"] = hotel_id

            await self._batch_insert_supplier_hotel_mappings(hotel_code_map)
            sync_stats = await self._sync_extended_hotel_data(hotel_data_map, unique_key_to_id)
            for k, v in sync_stats.items():
                if k in stats:
                    stats[k] += int(v)
            await self._session.flush()
        except Exception as exc:
            logger.exception("HotelCrsService.deduplicate_and_insert error: %s", exc)
            stats["errors"] += 1
        return stats

    async def batch_get_or_create_suppliers(
        self, booking_sources: list[str]
    ) -> dict[str, str]:
        supplier_map: dict[str, str] = {}
        if not booking_sources:
            return supplier_map
        registry = get_integration_registry()
        now = timeutils.datetime_now()
        for source in booking_sources:
            api = registry.resolve_booking_api(source, sub_module="HOTEL") or registry.resolve_booking_api(
                source
            )
            if api is None or not api.status:
                logger.warning("HotelCrsService: BookingApi not found for source %s", source)
                continue
            stmt = select(HotelCrsSupplierRow).where(
                HotelCrsSupplierRow.booking_source_id == str(api.id),
                HotelCrsSupplierRow.supplier_type == CrsSupplierTypeEnum.API.value,
            )
            row = (await self._session.execute(stmt)).scalar_one_or_none()
            if row is None:
                row = HotelCrsSupplierRow(
                    id=str(uuid.uuid4()),
                    booking_source_id=str(api.id),
                    supplier_type=CrsSupplierTypeEnum.API.value,
                    user_id=None,
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(row)
                await self._session.flush()
            supplier_map[source] = row.id
        return supplier_map

    async def _batch_find_existing_hotels(
        self, city_id: str, lookup_keys: list[str]
    ) -> list[HotelCrsHotelRow]:
        star_ratings: list[int] = []
        for key in lookup_keys:
            parts = key.split("|")
            if len(parts) > 1 and int(parts[1]) > 0:
                star_ratings.append(int(parts[1]))
        star_ratings = list(set(star_ratings))
        stmt = select(HotelCrsHotelRow).where(
            HotelCrsHotelRow.city_id == city_id,
            HotelCrsHotelRow.status.is_(True),
        )
        if star_ratings:
            stmt = stmt.where(HotelCrsHotelRow.star_rating.in_(star_ratings))
        stmt = stmt.limit(500)
        return list((await self._session.execute(stmt)).scalars().all())

    def _build_insert_row(
        self,
        hotel: dict[str, Any],
        data: dict[str, Any],
        city_id: str,
        unique_key: str,
    ) -> dict[str, Any]:
        address = str(hotel.get("address") or hotel.get("HotelAddress") or "")
        parts = HotelCommon.split_address(address)
        geo = hotel.get("geoPoint") if isinstance(hotel.get("geoPoint"), dict) else {}
        lat = geo.get("lat")
        lng = geo.get("lng")
        image = str(hotel.get("image") or hotel.get("HotelPicture") or "")
        images = hotel.get("images") if isinstance(hotel.get("images"), list) else []
        now = timeutils.datetime_now()
        return {
            "id": str(uuid.uuid4()),
            "code": HotelCommon.generate_hotel_code(),
            "name": data["name"],
            "name_normalized": data["name_normalized"],
            "star_rating": data["star"],
            "unique_key": unique_key,
            "city_id": city_id,
            "address_line1": parts["line1"] or None,
            "address_line2": parts["line2"] or None,
            "postal_code": str(hotel.get("zipCode") or "") or None,
            "location": str(hotel.get("location") or "") or None,
            "latitude": Decimal(str(lat)) if lat is not None else None,
            "longitude": Decimal(str(lng)) if lng is not None else None,
            "phone": str(hotel.get("hotelPhone") or hotel.get("HotelContactNo") or "") or None,
            "email": str(hotel.get("email") or "") or None,
            "check_in_time": str(hotel.get("checkIn") or "14:00:00"),
            "check_out_time": str(hotel.get("checkOut") or "12:00:00"),
            "front_desk_time_start": str(hotel.get("front_desk_time_start") or "") or None,
            "front_desk_time_end": str(hotel.get("front_desk_time_end") or "") or None,
            "description": str(hotel.get("description") or hotel.get("HotelDescription") or "")
            or None,
            "policy_text": self._build_policy_text(hotel),
            "hotel_policies": self._build_hotel_policies_html(hotel),
            "meta": self._build_meta_payload(hotel),
            "image": image or None,
            "status": True,
            "created_at": now,
            "updated_at": now,
            "_unique_key": unique_key,
            "_images": images,
        }

    async def _batch_insert_hotels(
        self, hotels_data: list[dict[str, Any]], city_id: str
    ) -> dict[str, str]:
        unique_key_to_id: dict[str, str] = {}
        for i in range(0, len(hotels_data), BATCH_SIZE):
            chunk = hotels_data[i : i + BATCH_SIZE]
            images_by_key: dict[str, list[Any]] = {}
            for row in chunk:
                uk = row["_unique_key"]
                images_by_key[uk] = row.pop("_images", [])
                row.pop("_unique_key", None)
                self._session.add(HotelCrsHotelRow(**row))
                unique_key_to_id[uk] = row["id"]
            await self._session.flush()
            for uk, hotel_id in list(unique_key_to_id.items()):
                if uk in images_by_key and images_by_key[uk]:
                    await self._insert_hotel_images(hotel_id, images_by_key[uk])
        return unique_key_to_id

    async def _insert_hotel_images(self, hotel_id: str, images: list[Any]) -> int:
        now = timeutils.datetime_now()
        seen: set[str] = set()
        count = 0
        for idx, img in enumerate(images):
            if not isinstance(img, dict):
                continue
            url = str(img.get("url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            self._session.add(
                HotelCrsHotelImageRow(
                    id=str(uuid.uuid4()),
                    hotel_id=hotel_id,
                    url=url,
                    caption=str(img.get("caption") or "") or None,
                    category_slug=str(img.get("category_slug") or "") or None,
                    sort_order=idx,
                    created_at=now,
                    updated_at=now,
                )
            )
            count += 1
        return count

    async def _batch_insert_supplier_hotel_mappings(
        self, hotel_code_map: dict[str, dict[str, Any]]
    ) -> None:
        if not hotel_code_map:
            return
        supplier_ids = list({d["supplier_id"] for d in hotel_code_map.values()})
        hotel_ids = [d["crs_hotel_id"] for d in hotel_code_map.values() if d.get("crs_hotel_id")]
        if not hotel_ids:
            return
        existing_rows = (
            await self._session.execute(
                select(
                    HotelCrsSupplierHotelMapRow.supplier_id,
                    HotelCrsSupplierHotelMapRow.supplier_hotel_code,
                    HotelCrsSupplierHotelMapRow.hotel_id,
                ).where(
                    HotelCrsSupplierHotelMapRow.supplier_id.in_(supplier_ids),
                    HotelCrsSupplierHotelMapRow.hotel_id.in_(hotel_ids),
                )
            )
        ).all()
        existing = {
            f"{r[0]}|{r[1]}|{r[2]}": True for r in existing_rows
        }
        now = timeutils.datetime_now()
        for data in hotel_code_map.values():
            if not data.get("crs_hotel_id") or not data.get("hotel_code"):
                continue
            key = f"{data['supplier_id']}|{data['hotel_code']}|{data['crs_hotel_id']}"
            if key in existing:
                continue
            self._session.add(
                HotelCrsSupplierHotelMapRow(
                    id=str(uuid.uuid4()),
                    supplier_id=data["supplier_id"],
                    supplier_hotel_code=data["hotel_code"],
                    hotel_id=data["crs_hotel_id"],
                    meta=None,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def _sync_extended_hotel_data(
        self,
        hotel_data_map: dict[str, dict[str, Any]],
        unique_key_to_id: dict[str, str],
    ) -> dict[str, int]:
        stats = {
            "hotelImagesSynced": 0,
            "hotelAmenitiesMapped": 0,
            "roomGroupsSynced": 0,
            "roomImagesSynced": 0,
            "roomAmenitiesMapped": 0,
        }
        if not unique_key_to_id:
            return stats
        amenity_master_map = await self._prepare_amenity_master_map(hotel_data_map)
        now = timeutils.datetime_now()
        for unique_key, row in hotel_data_map.items():
            hotel_id = unique_key_to_id.get(unique_key)
            if not hotel_id:
                continue
            hotel = row.get("hotel") if isinstance(row.get("hotel"), dict) else {}
            await self._session.execute(
                delete(HotelCrsHotelImageRow).where(HotelCrsHotelImageRow.hotel_id == hotel_id)
            )
            images = hotel.get("images") if isinstance(hotel.get("images"), list) else []
            stats["hotelImagesSynced"] += await self._insert_hotel_images(hotel_id, images)

            hotel_row = await self._session.get(HotelCrsHotelRow, hotel_id)
            if hotel_row:
                hotel_row.email = str(hotel.get("email") or "") or None
                hotel_row.check_in_time = str(hotel.get("checkIn") or "14:00:00")
                hotel_row.check_out_time = str(hotel.get("checkOut") or "12:00:00")
                hotel_row.front_desk_time_start = (
                    str(hotel.get("front_desk_time_start") or "") or None
                )
                hotel_row.front_desk_time_end = str(hotel.get("front_desk_time_end") or "") or None
                hotel_row.description = str(hotel.get("description") or "") or None
                hotel_row.policy_text = self._build_policy_text(hotel)
                hotel_row.hotel_policies = self._build_hotel_policies_html(hotel)
                hotel_row.meta = self._build_meta_payload(hotel)
                hotel_row.updated_at = now

            stats["hotelAmenitiesMapped"] += await self._sync_hotel_amenities(
                hotel_id, hotel, amenity_master_map
            )
            room_stats = await self._sync_hotel_rooms(hotel_id, hotel, amenity_master_map)
            stats["roomGroupsSynced"] += room_stats["roomGroupsSynced"]
            stats["roomImagesSynced"] += room_stats["roomImagesSynced"]
            stats["roomAmenitiesMapped"] += room_stats["roomAmenitiesMapped"]
        return stats

    async def _prepare_amenity_master_map(
        self, hotel_data_map: dict[str, dict[str, Any]]
    ) -> dict[str, str]:
        rows: dict[str, dict[str, Any]] = {}
        now = timeutils.datetime_now()
        for item in hotel_data_map.values():
            hotel = item.get("hotel") if isinstance(item.get("hotel"), dict) else {}
            for amenity_item in self._extract_hotel_amenity_items(hotel):
                slug = self._amenity_slug(str(amenity_item.get("name") or ""))
                if not slug:
                    continue
                rows[slug] = {
                    "slug": slug,
                    "name": str(amenity_item.get("name") or slug),
                    "scope": "both",
                }
            for room in hotel.get("room_groups") or []:
                if not isinstance(room, dict):
                    continue
                for amenity_name in room.get("room_amenities") or []:
                    slug = self._amenity_slug(str(amenity_name))
                    if not slug:
                        continue
                    rows[slug] = {
                        "slug": slug,
                        "name": self._normalize_amenity_display_name(str(amenity_name)),
                        "scope": "both",
                    }
        if not rows:
            return {}
        for slug, data in rows.items():
            existing = (
                await self._session.execute(
                    select(HotelCrsAmenityRow).where(HotelCrsAmenityRow.slug == slug)
                )
            ).scalar_one_or_none()
            if existing:
                existing.name = data["name"]
                existing.scope = data["scope"]
                existing.updated_at = now
            else:
                self._session.add(
                    HotelCrsAmenityRow(
                        id=str(uuid.uuid4()),
                        slug=slug,
                        name=data["name"],
                        category=None,
                        image_file_id=None,
                        scope=data["scope"],
                        created_at=now,
                        updated_at=now,
                    )
                )
        await self._session.flush()
        result = (
            await self._session.execute(
                select(HotelCrsAmenityRow.slug, HotelCrsAmenityRow.id).where(
                    HotelCrsAmenityRow.slug.in_(list(rows.keys()))
                )
            )
        ).all()
        return {str(slug): str(aid) for slug, aid in result}

    async def _sync_hotel_amenities(
        self,
        hotel_id: str,
        hotel: dict[str, Any],
        amenity_master_map: dict[str, str],
    ) -> int:
        await self._session.execute(
            delete(HotelCrsHotelAmenityMapRow).where(
                HotelCrsHotelAmenityMapRow.hotel_id == hotel_id
            )
        )
        items = self._extract_hotel_amenity_items(hotel)
        if not items:
            return 0
        now = timeutils.datetime_now()
        dedupe: set[str] = set()
        count = 0
        for item in items:
            name = str(item.get("name") or "")
            group_name = str(item.get("group_name") or "")
            is_paid = bool(item.get("is_paid") or False)
            slug = self._amenity_slug(name)
            amenity_id = amenity_master_map.get(slug)
            if not amenity_id:
                continue
            key = f"{amenity_id}|{group_name}"
            if key in dedupe:
                continue
            dedupe.add(key)
            self._session.add(
                HotelCrsHotelAmenityMapRow(
                    id=str(uuid.uuid4()),
                    hotel_id=hotel_id,
                    amenity_id=amenity_id,
                    group_name=group_name or None,
                    is_paid=is_paid,
                    created_at=now,
                    updated_at=now,
                )
            )
            count += 1
        return count

    async def _sync_hotel_rooms(
        self,
        hotel_id: str,
        hotel: dict[str, Any],
        amenity_master_map: dict[str, str],
    ) -> dict[str, int]:
        stats = {
            "roomGroupsSynced": 0,
            "roomImagesSynced": 0,
            "roomAmenitiesMapped": 0,
        }
        existing_ids = list(
            (
                await self._session.execute(
                    select(HotelCrsRoomGroupRow.id).where(
                        HotelCrsRoomGroupRow.hotel_id == hotel_id
                    )
                )
            )
            .scalars()
            .all()
        )
        if existing_ids:
            await self._session.execute(
                delete(HotelCrsRoomAmenityMapRow).where(
                    HotelCrsRoomAmenityMapRow.room_group_id.in_(existing_ids)
                )
            )
            await self._session.execute(
                delete(HotelCrsRoomImageRow).where(
                    HotelCrsRoomImageRow.room_group_id.in_(existing_ids)
                )
            )
            await self._session.execute(
                delete(HotelCrsRoomGroupRow).where(HotelCrsRoomGroupRow.id.in_(existing_ids))
            )

        room_groups = hotel.get("room_groups") if isinstance(hotel.get("room_groups"), list) else []
        if not room_groups:
            return stats

        now = timeutils.datetime_now()
        room_context_by_code: dict[str, dict[str, Any]] = {}
        inserted: list[tuple[str, str]] = []  # (room_id, supplier_code)

        for room in room_groups:
            if not isinstance(room, dict):
                continue
            supplier_room_code = str(room.get("room_group_id") or "")
            if not supplier_room_code or supplier_room_code in room_context_by_code:
                continue
            name_struct = room.get("name_struct") if isinstance(room.get("name_struct"), dict) else {}
            rg_ext = room.get("rg_ext") if isinstance(room.get("rg_ext"), dict) else {}
            capacity = int(rg_ext["capacity"]) if rg_ext.get("capacity") is not None else None
            if capacity is not None and capacity <= 0:
                capacity = None
            room_id = str(uuid.uuid4())
            self._session.add(
                HotelCrsRoomGroupRow(
                    id=room_id,
                    hotel_id=hotel_id,
                    supplier_room_code=supplier_room_code,
                    name=str(name_struct.get("main_name") or ""),
                    main_name=str(name_struct.get("main_name") or "") or None,
                    bedding_type=str(name_struct.get("bedding_type") or "") or None,
                    bathroom_type=str(name_struct.get("bathroom") or "") or None,
                    size=_safe_decimal(room.get("size")),
                    capacity=capacity,
                    rg_ext=rg_ext or None,
                    raw=room,
                    created_at=now,
                    updated_at=now,
                )
            )
            room_context_by_code[supplier_room_code] = room
            inserted.append((room_id, supplier_room_code))
            stats["roomGroupsSynced"] += 1

        await self._session.flush()
        amenity_dedupe: set[str] = set()
        for room_id, supplier_room_code in inserted:
            room_raw = room_context_by_code.get(supplier_room_code) or {}
            for idx, img in enumerate(self._extract_room_images(room_raw)):
                self._session.add(
                    HotelCrsRoomImageRow(
                        id=str(uuid.uuid4()),
                        room_group_id=room_id,
                        url=str(img.get("url") or ""),
                        category_slug=str(img.get("category_slug") or "") or None,
                        sort_order=idx,
                        created_at=now,
                        updated_at=now,
                    )
                )
                stats["roomImagesSynced"] += 1
            for amenity_name in room_raw.get("room_amenities") or []:
                slug = self._amenity_slug(str(amenity_name))
                amenity_id = amenity_master_map.get(slug)
                if not amenity_id:
                    continue
                k = f"{room_id}|{amenity_id}"
                if k in amenity_dedupe:
                    continue
                amenity_dedupe.add(k)
                self._session.add(
                    HotelCrsRoomAmenityMapRow(
                        id=str(uuid.uuid4()),
                        room_group_id=room_id,
                        amenity_id=amenity_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
                stats["roomAmenitiesMapped"] += 1
        return stats

    def _extract_hotel_amenity_items(self, hotel: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for group in hotel.get("amenity_groups") or []:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("group_name") or "")
            non_free = group.get("non_free_amenities") or []
            non_free_map = {self._amenity_slug(str(nf)): True for nf in non_free}
            for name in group.get("amenities") or []:
                slug = self._amenity_slug(str(name))
                if not slug:
                    continue
                items.append(
                    {
                        "name": self._normalize_amenity_display_name(str(name)),
                        "group_name": group_name,
                        "is_paid": slug in non_free_map,
                    }
                )
        if not items:
            for name in hotel.get("allamenities") or []:
                slug = self._amenity_slug(str(name))
                if not slug:
                    continue
                items.append(
                    {
                        "name": self._normalize_amenity_display_name(str(name)),
                        "group_name": "",
                        "is_paid": False,
                    }
                )
        return items

    def _extract_room_images(self, room: dict[str, Any]) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        seen: set[str] = set()
        for img in room.get("images_ext") or []:
            if not isinstance(img, dict):
                continue
            url = str(img.get("url") or "").replace("{size}", "1080x")
            if not url or url in seen:
                continue
            seen.add(url)
            images.append({"url": url, "category_slug": str(img.get("category_slug") or "")})
        if not images:
            for url in room.get("images") or []:
                url = str(url).replace("{size}", "1080x")
                if not url or url in seen:
                    continue
                seen.add(url)
                images.append({"url": url, "category_slug": ""})
        return images

    @staticmethod
    def _amenity_slug(name: str) -> str:
        name = name.strip().lower()
        if not name:
            return ""
        name = re.sub(r"[^a-z0-9]+", "-", name)
        return name.strip("-")

    @staticmethod
    def _normalize_amenity_display_name(name: str) -> str:
        name = name.strip().replace("_", " ").replace("-", " ")
        return name.title() if name else ""

    def _build_policy_text(self, hotel: dict[str, Any]) -> str | None:
        parts: list[str] = []
        for block in hotel.get("policy_struct") or []:
            if not isinstance(block, dict):
                continue
            title = str(block.get("title") or "").strip()
            paragraphs = block.get("paragraphs") if isinstance(block.get("paragraphs"), list) else []
            paragraph_text = "\n".join(str(p) for p in paragraphs if p).strip()
            if title:
                parts.append(title)
            if paragraph_text:
                parts.append(paragraph_text)
        extra = str(hotel.get("metapolicy_extra_info") or "").strip()
        if extra:
            parts.append(extra)
        out = "\n\n".join(parts).strip()
        return out or None

    def _build_hotel_policies_html(self, hotel: dict[str, Any]) -> str | None:
        meta = hotel.get("metapolicy_struct") if isinstance(hotel.get("metapolicy_struct"), dict) else {}
        points: list[str] = []
        # Keep a compact subset of policy lines (full PHP coverage is large; key categories)
        for item in self._to_policy_items(meta.get("deposit")):
            points.append(
                f"Deposit is {self._pv(item, 'availability')} to have. "
                f"{self._pv(item, 'deposit_type')} {self._pv(item, 'payment_type')} "
                f"{self._pv(item, 'pricing_method')}. The price is {self._pv(item, 'price')} "
                f"{self._pv(item, 'currency')} {self._pv(item, 'price_unit')}."
            )
        for item in self._to_policy_items(meta.get("internet")):
            points.append(
                f"{self._pv(item, 'type')} is {self._pv(item, 'inclusion')} to the overall price. "
                f"The price is {self._pv(item, 'price')} {self._pv(item, 'currency')} "
                f"{self._pv(item, 'price_unit')}. {self._pv(item, 'work_area')}."
            )
        for item in self._to_policy_items(meta.get("meal")):
            points.append(
                f"{self._pv(item, 'type')} is {self._pv(item, 'inclusion')} to the overall price. "
                f"The price is {self._pv(item, 'price')} {self._pv(item, 'currency')} per a person."
            )
        for item in self._to_policy_items(meta.get("pets")):
            points.append(
                f"Pet weight is {self._pv(item, 'pets_type')} is {self._pv(item, 'inclusion')} "
                f"to the overall price. The price is {self._pv(item, 'price')} "
                f"{self._pv(item, 'currency')} {self._pv(item, 'price_unit')}."
            )
        for item in self._to_policy_items(meta.get("parking")):
            points.append(
                f"Parking is {self._pv(item, 'territory_type')} and {self._pv(item, 'inclusion')} "
                f"to the overall price. The price is {self._pv(item, 'price')} "
                f"{self._pv(item, 'currency')} {self._pv(item, 'price_unit')}."
            )
        extra_info = str(hotel.get("metapolicy_extra_info") or "").strip()
        parts: list[str] = []
        if extra_info:
            parts.append(f"<p>{html.escape(extra_info).replace(chr(10), '<br>')}</p>")
        if points:
            parts.append(
                "<ul>" + "".join(f"<li>{html.escape(line)}</li>" for line in points) + "</ul>"
            )
        out = "\n".join(parts).strip()
        return out or None

    @staticmethod
    def _to_policy_items(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, dict) and not isinstance(value, list):
            return []
        if isinstance(value, dict):
            if not value:
                return []
            if all(isinstance(k, str) for k in value.keys()) and not any(
                isinstance(k, int) for k in value.keys()
            ):
                # assoc dict → single item unless values are list of dicts
                if any(isinstance(v, dict) for v in value.values()) and not any(
                    k
                    in (
                        "availability",
                        "type",
                        "inclusion",
                        "price",
                        "currency",
                        "deposit_type",
                    )
                    for k in value
                ):
                    return []
                return [value]
            return []
        return [v for v in value if isinstance(v, dict)]

    @staticmethod
    def _pv(item: dict[str, Any], key: str, fallback: str = "unspecified") -> str:
        raw = item.get(key)
        if raw is None:
            return fallback
        text = str(raw).strip()
        return text if text else fallback

    @staticmethod
    def _build_meta_payload(hotel: dict[str, Any]) -> dict[str, Any] | None:
        meta = {
            "facts": hotel.get("facts"),
            "payment_methods": hotel.get("payment_methods"),
            "metapolicy_struct": hotel.get("metapolicy_struct"),
            "serp_filters": hotel.get("serp_filters"),
        }
        if any(meta.values()):
            return meta
        return None
