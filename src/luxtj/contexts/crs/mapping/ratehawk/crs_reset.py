"""Batched CRS wipe for one booking_source_id (RateHawk).

Deletes reverse of promote order, in small batches with a commit per batch,
so Postgres stays responsive and FKs never need to be disabled.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import db

_MAPPING_BATCH = 2000
_HOTEL_BATCH = 25
_STAGING_BATCH = 500
_ROOM_CHILD_BATCH = 200
# Fail fast if another worker still holds locks (instead of hanging forever).
_LOCK_TIMEOUT_MS = 8_000

ProgressCb = Callable[[str, dict[str, Any]], None]


def _empty_stats() -> dict[str, int]:
    return {
        "supplierMappingsDeleted": 0,
        "hotelsDeleted": 0,
        "hotelImagesDeleted": 0,
        "hotelAmenitiesDeleted": 0,
        "hotelRoomsDeleted": 0,
        "roomAmenitiesDeleted": 0,
        "roomImagesDeleted": 0,
        "suppliersDeleted": 0,
        "hotelIdsTargeted": 0,
        "stagingHotelsDeleted": 0,
        "stagingRoomsDeleted": 0,
        "orphanHotelsSwept": 0,
    }


def _log(msg: str) -> None:
    print(f"[ratehawk-wipe] {msg}", flush=True)


def _merge(stats: dict[str, int], delta: dict[str, int]) -> None:
    for key, value in delta.items():
        stats[key] = stats.get(key, 0) + int(value)


def _cursor():
    return db.db_cursor(lock_timeout_ms=_LOCK_TIMEOUT_MS)


def _supplier_ids(booking_source_id: str) -> list[str]:
    with _cursor() as (_, cur):
        cur.execute(
            "SELECT id FROM hotel_crs_suppliers WHERE booking_source_id = %s",
            (booking_source_id,),
        )
        return [str(r[0]) for r in cur.fetchall()]


def _hotel_ids_from_supplier_maps(
    supplier_ids: list[str],
    *,
    on_progress: ProgressCb | None,
    stats: dict[str, int],
) -> list[str]:
    if not supplier_ids:
        return []
    ids: list[str] = []
    if on_progress:
        on_progress("resolve_hotels", stats)
    for i in range(0, len(supplier_ids), 50):
        chunk = supplier_ids[i : i + 50]
        ph = ",".join(["%s"] * len(chunk))
        with _cursor() as (_, cur):
            cur.execute(
                f"""
                SELECT DISTINCT hotel_id
                FROM hotel_crs_supplier_hotel_map
                WHERE supplier_id IN ({ph})
                ORDER BY hotel_id
                """,
                tuple(chunk),
            )
            ids.extend(str(r[0]) for r in cur.fetchall())
        stats["hotelIdsTargeted"] = len(set(ids))
        if on_progress and i % 50 == 0:
            on_progress("resolve_hotels", stats)
    return sorted(set(ids))


def _delete_supplier_hotel_maps(
    supplier_ids: list[str],
    *,
    mapping_batch: int,
    stats: dict[str, int],
    on_progress: ProgressCb | None,
) -> None:
    if not supplier_ids:
        return
    if on_progress:
        on_progress("supplier_maps", stats)
    sph = ",".join(["%s"] * len(supplier_ids))
    while True:
        with _cursor() as (_, cur):
            cur.execute(
                f"""
                SELECT id FROM hotel_crs_supplier_hotel_map
                WHERE supplier_id IN ({sph})
                ORDER BY id
                LIMIT %s
                """,
                tuple(supplier_ids) + (mapping_batch,),
            )
            map_ids = [str(r[0]) for r in cur.fetchall()]
            if not map_ids:
                break
            mph = ",".join(["%s"] * len(map_ids))
            cur.execute(
                f"DELETE FROM hotel_crs_supplier_hotel_map WHERE id IN ({mph})",
                tuple(map_ids),
            )
            deleted = len(map_ids)
            stats["supplierMappingsDeleted"] += deleted
        _log(f"supplier_hotel_map deleted batch={deleted} total={stats['supplierMappingsDeleted']}")
        if on_progress:
            on_progress("supplier_maps", stats)


def _delete_hotel_subtree(hotel_ids: list[str]) -> dict[str, int]:
    """Delete one hotel batch: room children → hotel children → hotels.

    Each step commits separately so long deletes do not hold one giant transaction.
    """
    stats = {
        "hotelsDeleted": 0,
        "hotelImagesDeleted": 0,
        "hotelAmenitiesDeleted": 0,
        "hotelRoomsDeleted": 0,
        "roomAmenitiesDeleted": 0,
        "roomImagesDeleted": 0,
    }
    if not hotel_ids:
        return stats

    hph = ",".join(["%s"] * len(hotel_ids))
    with _cursor() as (_, cur):
        cur.execute(
            f"SELECT id FROM hotel_crs_room_groups WHERE hotel_id IN ({hph})",
            tuple(hotel_ids),
        )
        room_ids = [str(r[0]) for r in cur.fetchall()]

    if room_ids:
        for i in range(0, len(room_ids), _ROOM_CHILD_BATCH):
            chunk = room_ids[i : i + _ROOM_CHILD_BATCH]
            rph = ",".join(["%s"] * len(chunk))
            with _cursor() as (_, cur):
                cur.execute(
                    f"DELETE FROM hotel_crs_room_amenity_map WHERE room_group_id IN ({rph})",
                    tuple(chunk),
                )
                stats["roomAmenitiesDeleted"] += max(0, cur.rowcount or 0)
                cur.execute(
                    f"DELETE FROM hotel_crs_room_images WHERE room_group_id IN ({rph})",
                    tuple(chunk),
                )
                stats["roomImagesDeleted"] += max(0, cur.rowcount or 0)

        with _cursor() as (_, cur):
            cur.execute(
                f"DELETE FROM hotel_crs_room_groups WHERE hotel_id IN ({hph})",
                tuple(hotel_ids),
            )
            stats["hotelRoomsDeleted"] = max(0, cur.rowcount or 0)

    with _cursor() as (_, cur):
        cur.execute(
            f"DELETE FROM hotel_crs_hotel_amenity_map WHERE hotel_id IN ({hph})",
            tuple(hotel_ids),
        )
        stats["hotelAmenitiesDeleted"] = max(0, cur.rowcount or 0)
        cur.execute(
            f"DELETE FROM hotel_crs_hotel_images WHERE hotel_id IN ({hph})",
            tuple(hotel_ids),
        )
        stats["hotelImagesDeleted"] = max(0, cur.rowcount or 0)
        # Normalized content children (order matters for policy attrs)
        cur.execute(
            f"""
            DELETE FROM hotel_crs_hotel_policy_item_attrs
            WHERE policy_item_id IN (
                SELECT id FROM hotel_crs_hotel_policy_items WHERE hotel_id IN ({hph})
            )
            """,
            tuple(hotel_ids),
        )
        for table in (
            "hotel_crs_hotel_policy_items",
            "hotel_crs_hotel_policy_sections",
            "hotel_crs_hotel_description_sections",
            "hotel_crs_hotel_payment_methods",
            "hotel_crs_hotel_feature_tags",
            "hotel_crs_hotel_register_room_categories",
        ):
            cur.execute(f"DELETE FROM {table} WHERE hotel_id IN ({hph})", tuple(hotel_ids))
        cur.execute(
            f"DELETE FROM hotel_crs_hotels WHERE id IN ({hph})",
            tuple(hotel_ids),
        )
        stats["hotelsDeleted"] = max(0, cur.rowcount or 0)

    return stats


def _delete_orphan_hotels(
    hotel_ids: list[str],
    *,
    hotel_batch: int,
    stats: dict[str, int],
    on_progress: ProgressCb | None,
) -> None:
    if on_progress:
        on_progress("hotels", stats)
    for i in range(0, len(hotel_ids), hotel_batch):
        batch = hotel_ids[i : i + hotel_batch]
        if on_progress:
            stats["hotelsPending"] = max(0, len(hotel_ids) - i)
            on_progress("hotels", stats)
        with _cursor() as (_, cur):
            bph = ",".join(["%s"] * len(batch))
            cur.execute(
                f"""
                SELECT DISTINCT hotel_id
                FROM hotel_crs_supplier_hotel_map
                WHERE hotel_id IN ({bph})
                """,
                tuple(batch),
            )
            still = {str(r[0]) for r in cur.fetchall()}
        orphans = [h for h in batch if h not in still]
        if not orphans:
            continue
        delta = _delete_hotel_subtree(orphans)
        _merge(stats, delta)
        _log(
            f"hotels deleted batch={delta.get('hotelsDeleted', 0)} "
            f"total={stats['hotelsDeleted']} remaining≈{max(0, len(hotel_ids) - i - len(batch))}"
        )
        if on_progress:
            stats["hotelsPending"] = max(0, len(hotel_ids) - i - len(batch))
            on_progress("hotels", stats)
    stats.pop("hotelsPending", None)


def _sweep_unmapped_hotels(
    *,
    hotel_batch: int,
    stats: dict[str, int],
    on_progress: ProgressCb | None,
    max_rounds: int = 10_000,
) -> None:
    """Keep deleting CRS hotels with zero supplier maps (keyset pagination)."""
    if on_progress:
        on_progress("orphan_sweep", stats)
    after_id = ""
    for _ in range(max_rounds):
        with _cursor() as (_, cur):
            cur.execute(
                """
                SELECT h.id
                FROM hotel_crs_hotels h
                LEFT JOIN hotel_crs_supplier_hotel_map m ON m.hotel_id = h.id
                WHERE m.hotel_id IS NULL
                  AND h.id > %s
                ORDER BY h.id
                LIMIT %s
                """,
                (after_id, hotel_batch),
            )
            batch = [str(r[0]) for r in cur.fetchall()]
        if not batch:
            break
        delta = _delete_hotel_subtree(batch)
        _merge(stats, delta)
        stats["orphanHotelsSwept"] += int(delta.get("hotelsDeleted") or 0)
        _log(
            f"orphan sweep batch={delta.get('hotelsDeleted', 0)} "
            f"total_orphans={stats['orphanHotelsSwept']}"
        )
        if on_progress:
            on_progress("orphan_sweep", stats)
        after_id = batch[-1]


def clear_staging_batched(
    booking_source_id: str,
    *,
    batch_size: int = _STAGING_BATCH,
    stats: dict[str, int] | None = None,
    on_progress: ProgressCb | None = None,
) -> dict[str, int]:
    """Delete staging rows for a booking source in committed batches."""
    out = stats if stats is not None else {"stagingHotelsDeleted": 0, "stagingRoomsDeleted": 0}
    with _cursor() as (_, cur):
        cur.execute(
            "SELECT id FROM hotel_mapping_runs WHERE booking_source_id = %s",
            (booking_source_id,),
        )
        run_ids = [str(r[0]) for r in cur.fetchall()]
    if not run_ids:
        return out

    if on_progress:
        on_progress("staging_rooms", out)

    rph = ",".join(["%s"] * len(run_ids))
    while True:
        with _cursor() as (_, cur):
            cur.execute(
                f"""
                SELECT id FROM staging_rooms
                WHERE mapping_run_id IN ({rph})
                ORDER BY id
                LIMIT %s
                """,
                tuple(run_ids) + (batch_size,),
            )
            ids = [str(r[0]) for r in cur.fetchall()]
            if not ids:
                break
            iph = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM staging_rooms WHERE id IN ({iph})", tuple(ids))
            out["stagingRoomsDeleted"] += len(ids)
        if on_progress:
            on_progress("staging_rooms", out)

    if on_progress:
        on_progress("staging_hotels", out)

    while True:
        with _cursor() as (_, cur):
            cur.execute(
                f"""
                SELECT id FROM staging_hotels
                WHERE mapping_run_id IN ({rph})
                ORDER BY id
                LIMIT %s
                """,
                tuple(run_ids) + (batch_size,),
            )
            ids = [str(r[0]) for r in cur.fetchall()]
            if not ids:
                break
            iph = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM staging_hotels WHERE id IN ({iph})", tuple(ids))
            out["stagingHotelsDeleted"] += len(ids)
        if on_progress:
            on_progress("staging_hotels", out)

    return out


def reset_supplier_crs(
    booking_source_id: str,
    *,
    mapping_batch: int = _MAPPING_BATCH,
    hotel_batch: int = _HOTEL_BATCH,
    sweep_orphans: bool = True,
    clear_staging: bool = True,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    """Delete CRS + staging data for a booking source in reverse-insert batched order."""
    stats = _empty_stats()
    supplier_ids = _supplier_ids(booking_source_id)

    _log(
        f"start booking_source_id={booking_source_id} "
        f"suppliers={len(supplier_ids)} hotel_batch={hotel_batch}"
    )
    if on_progress:
        on_progress("start", stats)

    hotel_ids = _hotel_ids_from_supplier_maps(
        supplier_ids,
        on_progress=on_progress,
        stats=stats,
    )
    stats["hotelIdsTargeted"] = len(hotel_ids)
    _log(f"hotelIdsTargeted={stats['hotelIdsTargeted']}")
    if on_progress:
        on_progress("resolve_hotels", stats)

    if clear_staging:
        _log("phase: staging")
        clear_staging_batched(
            booking_source_id,
            stats=stats,
            on_progress=on_progress,
        )

    if supplier_ids:
        _log("phase: supplier hotel maps")
        _delete_supplier_hotel_maps(
            supplier_ids,
            mapping_batch=mapping_batch,
            stats=stats,
            on_progress=on_progress,
        )

    if hotel_ids:
        _log("phase: targeted orphan hotels")
        _delete_orphan_hotels(
            hotel_ids,
            hotel_batch=hotel_batch,
            stats=stats,
            on_progress=on_progress,
        )

    if sweep_orphans:
        _log("phase: sweep unmapped hotels")
        _sweep_unmapped_hotels(
            hotel_batch=hotel_batch,
            stats=stats,
            on_progress=on_progress,
        )

    if supplier_ids:
        _log("phase: suppliers")
        if on_progress:
            on_progress("suppliers", stats)
        sph = ",".join(["%s"] * len(supplier_ids))
        with _cursor() as (_, cur):
            cur.execute(
                f"DELETE FROM hotel_crs_suppliers WHERE id IN ({sph})",
                tuple(supplier_ids),
            )
            stats["suppliersDeleted"] = max(0, cur.rowcount or 0)
        if on_progress:
            on_progress("suppliers", stats)

    msg = "RateHawk hotel mapping data deleted successfully."
    if (
        stats["hotelsDeleted"] == 0
        and stats["supplierMappingsDeleted"] == 0
        and stats["suppliersDeleted"] == 0
        and stats["stagingHotelsDeleted"] == 0
        and stats["stagingRoomsDeleted"] == 0
        and stats["orphanHotelsSwept"] == 0
    ):
        msg = "Nothing to reset."

    _log(f"done: {msg}")
    if on_progress:
        on_progress("done", stats)
    return {"message": msg, "stats": stats, "done": True}
