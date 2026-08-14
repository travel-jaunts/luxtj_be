"""Admin CRS hotel inventory queries (list / hotel detail / room detail)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.crs.infrastructure.persistence.sqlalchemy_models import (
    HotelCrsAmenityRow,
    HotelCrsHotelAmenityMapRow,
    HotelCrsHotelDescriptionSectionRow,
    HotelCrsHotelFeatureTagRow,
    HotelCrsHotelImageRow,
    HotelCrsHotelPaymentMethodRow,
    HotelCrsHotelPolicySectionRow,
    HotelCrsHotelRow,
    HotelCrsRoomAmenityMapRow,
    HotelCrsRoomGroupRow,
    HotelCrsRoomImageRow,
    HotelCrsSupplierHotelMapRow,
    HotelCrsSupplierRow,
    NewCitiesNRegionRow,
)
from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_models import (
    BookingApiRow,
)

_MAX_PAGE_SIZE = 50
_DEFAULT_PAGE_SIZE = 25


def _normalize_name_token(value: str) -> str:
    lowered = value.strip().lower()
    return re.sub(r"[^a-z0-9]", "", lowered)


def _clip_page(page: int, page_size: int) -> tuple[int, int]:
    page_n = max(1, int(page or 1))
    size = min(_MAX_PAGE_SIZE, max(1, int(page_size or _DEFAULT_PAGE_SIZE)))
    return page_n, size


def _dec(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _hotel_list_item(
    row: HotelCrsHotelRow,
    *,
    region_name: str | None = None,
    room_count: int | None = None,
    amenity_names: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "starRating": int(row.star_rating or 0),
        "status": bool(row.status),
        "image": row.image,
        "addressLine1": row.address_line1,
        "addressLine2": row.address_line2,
        "location": row.location,
        "postalCode": row.postal_code,
        "latitude": _dec(row.latitude),
        "longitude": _dec(row.longitude),
        "regionId": row.region_id,
        "regionName": region_name,
        "roomCount": int(room_count or 0),
        "accommodationType": row.accommodation_type,
        "hotelChain": row.hotel_chain,
        "amenities": list(amenity_names or [])[:6],
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _search_filters(q: str) -> list[Any]:
    raw = (q or "").strip()
    if not raw:
        return []
    like = f"%{raw}%"
    clauses: list[Any] = [
        HotelCrsHotelRow.code.ilike(like),
        HotelCrsHotelRow.name.ilike(like),
        HotelCrsHotelRow.address_line1.ilike(like),
        HotelCrsHotelRow.address_line2.ilike(like),
        HotelCrsHotelRow.location.ilike(like),
    ]
    norm = _normalize_name_token(raw)
    if len(norm) >= 2:
        # name_normalized stores alnum-only lowercase — prefix/contains via trigram.
        clauses.append(HotelCrsHotelRow.name_normalized.ilike(f"%{norm}%"))
        # Prefer prefix when the token is reasonably long (btree-friendly path too).
        if len(norm) >= 3:
            clauses.append(HotelCrsHotelRow.name_normalized.like(f"{norm}%"))
    return [or_(*clauses)]


async def _estimated_hotel_count(crs: AsyncSession) -> int:
    """Planner estimate — O(1). Exact COUNT(*) is too expensive at multi-million scale."""
    result = await crs.execute(
        text(
            "SELECT COALESCE(reltuples, 0)::bigint "
            "FROM pg_class WHERE relname = 'hotel_crs_hotels' LIMIT 1"
        )
    )
    estimate = result.scalar_one_or_none()
    if estimate is None:
        return 0
    return max(0, int(estimate))


def _hotel_filter_stmt(*, q: str, status: bool | None) -> Select[Any]:
    stmt = select(HotelCrsHotelRow.id)
    if status is not None:
        stmt = stmt.where(HotelCrsHotelRow.status.is_(status))
    for clause in _search_filters(q):
        stmt = stmt.where(clause)
    return stmt


def _list_base_query(*, q: str, status: bool | None) -> Select[Any]:
    room_count = (
        select(func.count())
        .select_from(HotelCrsRoomGroupRow)
        .where(HotelCrsRoomGroupRow.hotel_id == HotelCrsHotelRow.id)
        .correlate(HotelCrsHotelRow)
        .scalar_subquery()
        .label("room_count")
    )
    stmt = select(
        HotelCrsHotelRow,
        NewCitiesNRegionRow.name.label("region_name"),
        room_count,
    ).outerjoin(
        NewCitiesNRegionRow,
        NewCitiesNRegionRow.id == HotelCrsHotelRow.region_id,
    )
    if status is not None:
        stmt = stmt.where(HotelCrsHotelRow.status.is_(status))
    for clause in _search_filters(q):
        stmt = stmt.where(clause)
    return stmt


async def list_hotels(
    crs: AsyncSession,
    *,
    q: str = "",
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    status: bool | None = True,
) -> dict[str, Any]:
    page_n, size = _clip_page(page, page_size)
    offset = (page_n - 1) * size
    has_search = bool((q or "").strip())

    base = _list_base_query(q=q, status=status)
    rows_stmt = (
        base.order_by(HotelCrsHotelRow.created_at.desc(), HotelCrsHotelRow.id.desc())
        .offset(offset)
        .limit(size)
    )
    rows = (await crs.execute(rows_stmt)).all()

    hotel_ids = [hotel.id for hotel, _, _ in rows]
    amenities_by_hotel: dict[str, list[str]] = {hid: [] for hid in hotel_ids}
    if hotel_ids:
        amenity_rows = (
            await crs.execute(
                select(
                    HotelCrsHotelAmenityMapRow.hotel_id,
                    HotelCrsAmenityRow.name,
                )
                .join(
                    HotelCrsAmenityRow,
                    HotelCrsAmenityRow.id == HotelCrsHotelAmenityMapRow.amenity_id,
                )
                .where(HotelCrsHotelAmenityMapRow.hotel_id.in_(hotel_ids))
                .order_by(
                    HotelCrsHotelAmenityMapRow.hotel_id.asc(),
                    HotelCrsAmenityRow.name.asc(),
                )
            )
        ).all()
        for hotel_id, amenity_name in amenity_rows:
            bucket = amenities_by_hotel.setdefault(str(hotel_id), [])
            if len(bucket) >= 6:
                continue
            label = str(amenity_name or "").strip()
            if label and label not in bucket:
                bucket.append(label)

    if has_search or status is not True:
        count_stmt = select(func.count()).select_from(
            _hotel_filter_stmt(q=q, status=status).subquery()
        )
        total = int((await crs.execute(count_stmt)).scalar_one() or 0)
        total_is_estimate = False
    else:
        # Unfiltered active browse: never COUNT(*) the full multi-million table.
        total = await _estimated_hotel_count(crs)
        total_is_estimate = True

    items = [
        _hotel_list_item(
            hotel,
            region_name=region_name,
            room_count=room_count,
            amenity_names=amenities_by_hotel.get(hotel.id) or [],
        )
        for hotel, region_name, room_count in rows
    ]
    return {
        "items": items,
        "page": page_n,
        "pageSize": size,
        "total": total,
        "totalIsEstimate": total_is_estimate,
        "hasMore": offset + len(items) < total if not total_is_estimate else len(items) == size,
    }


async def _booking_api_lookup(
    main: AsyncSession,
    booking_source_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not booking_source_ids:
        return {}
    rows = (
        (
            await main.execute(
                select(BookingApiRow).where(BookingApiRow.id.in_(list(set(booking_source_ids))))
            )
        )
        .scalars()
        .all()
    )
    return {
        row.id: {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "status": bool(row.status),
        }
        for row in rows
    }


async def _hotel_suppliers(
    crs: AsyncSession,
    main: AsyncSession,
    hotel_id: str,
) -> list[dict[str, Any]]:
    stmt = (
        select(HotelCrsSupplierHotelMapRow, HotelCrsSupplierRow)
        .join(
            HotelCrsSupplierRow,
            HotelCrsSupplierRow.id == HotelCrsSupplierHotelMapRow.supplier_id,
        )
        .where(HotelCrsSupplierHotelMapRow.hotel_id == hotel_id)
        .order_by(HotelCrsSupplierRow.created_at.asc())
    )
    pairs = (await crs.execute(stmt)).all()
    api_map = await _booking_api_lookup(
        main,
        [str(supplier.booking_source_id) for _, supplier in pairs],
    )
    out: list[dict[str, Any]] = []
    for mapping, supplier in pairs:
        api = api_map.get(str(supplier.booking_source_id))
        out.append(
            {
                "mapId": mapping.id,
                "supplierId": supplier.id,
                "supplierType": supplier.supplier_type,
                "bookingSourceId": supplier.booking_source_id,
                "bookingSourceCode": (api or {}).get("code"),
                "bookingSourceName": (api or {}).get("name"),
                "supplierHotelCode": mapping.supplier_hotel_code,
                "meta": mapping.meta,
                "createdAt": mapping.created_at.isoformat() if mapping.created_at else None,
            }
        )
    return out


async def _hotel_amenities(crs: AsyncSession, hotel_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(HotelCrsHotelAmenityMapRow, HotelCrsAmenityRow)
        .join(
            HotelCrsAmenityRow,
            HotelCrsAmenityRow.id == HotelCrsHotelAmenityMapRow.amenity_id,
        )
        .where(HotelCrsHotelAmenityMapRow.hotel_id == hotel_id)
        .order_by(HotelCrsAmenityRow.name.asc())
    )
    return [
        {
            "id": amenity.id,
            "slug": amenity.slug,
            "name": amenity.name,
            "category": amenity.category,
            "scope": amenity.scope,
            "groupName": link.group_name,
            "isPaid": bool(link.is_paid),
        }
        for link, amenity in (await crs.execute(stmt)).all()
    ]


async def _hotel_images(crs: AsyncSession, hotel_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(HotelCrsHotelImageRow)
        .where(HotelCrsHotelImageRow.hotel_id == hotel_id)
        .order_by(HotelCrsHotelImageRow.sort_order.asc(), HotelCrsHotelImageRow.created_at.asc())
    )
    return [
        {
            "id": img.id,
            "url": img.url,
            "caption": img.caption,
            "categorySlug": img.category_slug,
            "sortOrder": img.sort_order,
        }
        for img in (await crs.execute(stmt)).scalars().all()
    ]


async def _hotel_rooms_summary(crs: AsyncSession, hotel_id: str) -> list[dict[str, Any]]:
    rooms = (
        (
            await crs.execute(
                select(HotelCrsRoomGroupRow)
                .where(HotelCrsRoomGroupRow.hotel_id == hotel_id)
                .order_by(HotelCrsRoomGroupRow.name.asc(), HotelCrsRoomGroupRow.id.asc())
            )
        )
        .scalars()
        .all()
    )
    if not rooms:
        return []

    room_ids = [r.id for r in rooms]
    images_by_room: dict[str, list[str]] = {rid: [] for rid in room_ids}
    image_counts: dict[str, int] = dict.fromkeys(room_ids, 0)
    img_rows = (
        (
            await crs.execute(
                select(HotelCrsRoomImageRow)
                .where(HotelCrsRoomImageRow.room_group_id.in_(room_ids))
                .order_by(
                    HotelCrsRoomImageRow.room_group_id.asc(),
                    HotelCrsRoomImageRow.sort_order.asc(),
                    HotelCrsRoomImageRow.created_at.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    for img in img_rows:
        image_counts[img.room_group_id] = image_counts.get(img.room_group_id, 0) + 1
        bucket = images_by_room.setdefault(img.room_group_id, [])
        if len(bucket) < 12:
            bucket.append(img.url)

    amenities_by_room: dict[str, list[str]] = {rid: [] for rid in room_ids}
    amenity_counts: dict[str, int] = dict.fromkeys(room_ids, 0)
    amenity_rows = (
        await crs.execute(
            select(
                HotelCrsRoomAmenityMapRow.room_group_id,
                HotelCrsAmenityRow.name,
            )
            .join(
                HotelCrsAmenityRow,
                HotelCrsAmenityRow.id == HotelCrsRoomAmenityMapRow.amenity_id,
            )
            .where(HotelCrsRoomAmenityMapRow.room_group_id.in_(room_ids))
            .order_by(
                HotelCrsRoomAmenityMapRow.room_group_id.asc(),
                HotelCrsAmenityRow.name.asc(),
            )
        )
    ).all()
    for room_id, amenity_name in amenity_rows:
        rid = str(room_id)
        amenity_counts[rid] = amenity_counts.get(rid, 0) + 1
        bucket = amenities_by_room.setdefault(rid, [])
        if len(bucket) >= 14:
            continue
        label = str(amenity_name or "").strip()
        if label and label not in bucket:
            bucket.append(label)

    return [
        {
            "id": room.id,
            "name": room.name,
            "mainName": room.main_name,
            "description": room.description,
            "supplierRoomCode": room.supplier_room_code,
            "beddingType": room.bedding_type,
            "bathroomType": room.bathroom_type,
            "size": _dec(room.size),
            "capacity": room.capacity,
            "bedrooms": room.bedrooms,
            "balcony": room.balcony,
            "viewType": room.view_type,
            "classLabel": room.class_label,
            "qualityLabel": room.quality_label,
            "gender": room.gender,
            "isFamily": room.is_family,
            "isClub": room.is_club,
            "floorType": room.floor_type,
            "imageCount": int(image_counts.get(room.id) or 0),
            "amenityCount": int(amenity_counts.get(room.id) or 0),
            "thumbnailUrl": (images_by_room.get(room.id) or [None])[0],
            "imageUrls": images_by_room.get(room.id) or [],
            "amenities": amenities_by_room.get(room.id) or [],
        }
        for room in rooms
    ]


async def get_hotel_detail(
    crs: AsyncSession,
    main: AsyncSession,
    hotel_id: str,
) -> dict[str, Any] | None:
    hotel = await crs.get(HotelCrsHotelRow, hotel_id)
    if hotel is None:
        # Allow lookup by CRS hotel code as well.
        hotel = (
            await crs.execute(select(HotelCrsHotelRow).where(HotelCrsHotelRow.code == hotel_id))
        ).scalar_one_or_none()
    if hotel is None:
        return None

    region_name = None
    country_name = None
    country_code = None
    if hotel.region_id:
        region = await crs.get(NewCitiesNRegionRow, hotel.region_id)
        if region is not None:
            region_name = region.name
            country_name = region.country_name
            country_code = region.country_code

    suppliers = await _hotel_suppliers(crs, main, hotel.id)
    amenities = await _hotel_amenities(crs, hotel.id)
    images = await _hotel_images(crs, hotel.id)
    rooms = await _hotel_rooms_summary(crs, hotel.id)

    return {
        **_hotel_list_item(hotel, region_name=region_name),
        "phone": hotel.phone,
        "email": hotel.email,
        "checkInTime": hotel.check_in_time,
        "checkInTimeEnd": hotel.check_in_time_end,
        "checkOutTime": hotel.check_out_time,
        "frontDeskTimeStart": hotel.front_desk_time_start,
        "frontDeskTimeEnd": hotel.front_desk_time_end,
        "description": hotel.description,
        "policyText": hotel.policy_text,
        "hotelPolicies": hotel.hotel_policies,
        "uniqueKey": hotel.unique_key,
        "accommodationType": hotel.accommodation_type,
        "accommodationTypeCode": hotel.accommodation_type_code,
        "hotelChain": hotel.hotel_chain,
        "giataCode": hotel.giata_code,
        "isClosed": hotel.is_closed,
        "isGenderSpecificationRequired": hotel.is_gender_specification_required,
        "floorsCount": hotel.floors_count,
        "roomsCount": hotel.rooms_count,
        "yearBuilt": hotel.year_built,
        "yearRenovated": hotel.year_renovated,
        "electricityFrequency": hotel.electricity_frequency,
        "electricityVoltage": hotel.electricity_voltage,
        "electricitySockets": hotel.electricity_sockets,
        "starCertificateId": hotel.star_certificate_id,
        "starCertificateValidTo": hotel.star_certificate_valid_to,
        "keysPickupType": hotel.keys_pickup_type,
        "keysPickupPhone": hotel.keys_pickup_phone,
        "keysPickupEmail": hotel.keys_pickup_email,
        "keysPickupIsContactless": hotel.keys_pickup_is_contactless,
        "keysPickupAddress": hotel.keys_pickup_address,
        "keysPickupExtraInfo": hotel.keys_pickup_extra_info,
        "registerRecord": hotel.register_record,
        "registerStatus": hotel.register_status,
        "registerKind": hotel.register_kind,
        "registerName": hotel.register_name,
        "externalCode": hotel.external_code,
        "supplierSlug": hotel.supplier_slug,
        "paymentMethods": [
            m.method_code
            for m in (
                await crs.execute(
                    select(HotelCrsHotelPaymentMethodRow).where(
                        HotelCrsHotelPaymentMethodRow.hotel_id == hotel.id
                    )
                )
            )
            .scalars()
            .all()
        ],
        "featureTags": [
            t.tag
            for t in (
                await crs.execute(
                    select(HotelCrsHotelFeatureTagRow).where(
                        HotelCrsHotelFeatureTagRow.hotel_id == hotel.id
                    )
                )
            )
            .scalars()
            .all()
        ],
        "descriptionSections": [
            {
                "id": s.id,
                "title": s.title,
                "body": s.body,
                "sortOrder": s.sort_order,
            }
            for s in (
                await crs.execute(
                    select(HotelCrsHotelDescriptionSectionRow)
                    .where(HotelCrsHotelDescriptionSectionRow.hotel_id == hotel.id)
                    .order_by(
                        HotelCrsHotelDescriptionSectionRow.sort_order.asc(),
                        HotelCrsHotelDescriptionSectionRow.created_at.asc(),
                    )
                )
            )
            .scalars()
            .all()
        ],
        "policySections": [
            {
                "id": s.id,
                "sectionType": s.section_type,
                "title": s.title,
                "body": s.body,
                "sortOrder": s.sort_order,
            }
            for s in (
                await crs.execute(
                    select(HotelCrsHotelPolicySectionRow)
                    .where(HotelCrsHotelPolicySectionRow.hotel_id == hotel.id)
                    .order_by(
                        HotelCrsHotelPolicySectionRow.sort_order.asc(),
                        HotelCrsHotelPolicySectionRow.created_at.asc(),
                    )
                )
            )
            .scalars()
            .all()
        ],
        "countryName": country_name,
        "countryCode": country_code,
        "suppliers": suppliers,
        "amenities": amenities,
        "images": images,
        "rooms": rooms,
        "roomCount": len(rooms),
        "amenityCount": len(amenities),
        "imageCount": len(images),
        "supplierCount": len(suppliers),
    }


async def _room_amenities(crs: AsyncSession, room_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(HotelCrsRoomAmenityMapRow, HotelCrsAmenityRow)
        .join(
            HotelCrsAmenityRow,
            HotelCrsAmenityRow.id == HotelCrsRoomAmenityMapRow.amenity_id,
        )
        .where(HotelCrsRoomAmenityMapRow.room_group_id == room_id)
        .order_by(HotelCrsAmenityRow.name.asc())
    )
    return [
        {
            "id": amenity.id,
            "slug": amenity.slug,
            "name": amenity.name,
            "category": amenity.category,
            "scope": amenity.scope,
        }
        for _, amenity in (await crs.execute(stmt)).all()
    ]


async def _room_images(crs: AsyncSession, room_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(HotelCrsRoomImageRow)
        .where(HotelCrsRoomImageRow.room_group_id == room_id)
        .order_by(HotelCrsRoomImageRow.sort_order.asc(), HotelCrsRoomImageRow.created_at.asc())
    )
    return [
        {
            "id": img.id,
            "url": img.url,
            "categorySlug": img.category_slug,
            "sortOrder": img.sort_order,
        }
        for img in (await crs.execute(stmt)).scalars().all()
    ]


async def get_room_detail(
    crs: AsyncSession,
    main: AsyncSession,
    hotel_id: str,
    room_id: str,
) -> dict[str, Any] | None:
    hotel = await crs.get(HotelCrsHotelRow, hotel_id)
    if hotel is None:
        hotel = (
            await crs.execute(select(HotelCrsHotelRow).where(HotelCrsHotelRow.code == hotel_id))
        ).scalar_one_or_none()
    if hotel is None:
        return None

    room = await crs.get(HotelCrsRoomGroupRow, room_id)
    if room is None or room.hotel_id != hotel.id:
        return None

    suppliers = await _hotel_suppliers(crs, main, hotel.id)
    # Room-level supplier identity is supplier_room_code; hotel maps provide the supplier.
    room_supplier_maps = [
        {
            **supplier,
            "supplierRoomCode": room.supplier_room_code,
        }
        for supplier in suppliers
    ]

    return {
        "id": room.id,
        "hotelId": hotel.id,
        "hotelCode": hotel.code,
        "hotelName": hotel.name,
        "name": room.name,
        "mainName": room.main_name,
        "description": room.description,
        "supplierRoomCode": room.supplier_room_code,
        "beddingType": room.bedding_type,
        "bathroomType": room.bathroom_type,
        "size": _dec(room.size),
        "capacity": room.capacity,
        "bedrooms": room.bedrooms,
        "balcony": room.balcony,
        "viewCode": room.view_code,
        "viewType": room.view_type,
        "roomClass": room.room_class,
        "classLabel": room.class_label,
        "quality": room.quality,
        "qualityLabel": room.quality_label,
        "gender": room.gender,
        "isFamily": room.is_family,
        "isClub": room.is_club,
        "floorType": room.floor_type,
        "createdAt": room.created_at.isoformat() if room.created_at else None,
        "updatedAt": room.updated_at.isoformat() if room.updated_at else None,
        "images": await _room_images(crs, room.id),
        "amenities": await _room_amenities(crs, room.id),
        "suppliers": room_supplier_maps,
    }
