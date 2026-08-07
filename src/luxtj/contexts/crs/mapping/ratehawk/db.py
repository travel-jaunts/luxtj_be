"""Sync DB helpers for RateHawk mapping workers (psycopg)."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Iterator
from uuid import uuid4

from . import config
from .parser import json_dumps


def _connect():
    import psycopg

    conn = psycopg.connect(config.database_url())
    conn.autocommit = False
    return conn


_tls = threading.local()


def _discard_cached_conn() -> None:
    conn = getattr(_tls, "conn", None)
    _tls.conn = None
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _get_conn():
    conn = getattr(_tls, "conn", None)
    if conn is not None:
        try:
            if not conn.closed:
                return conn
        except Exception:
            pass
        _discard_cached_conn()
    conn = _connect()
    _tls.conn = conn
    return conn


@contextmanager
def db_cursor(
    *,
    lock_timeout_ms: int | None = None,
    statement_timeout_ms: int | None = None,
) -> Iterator[Any]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
    except Exception:
        _discard_cached_conn()
        conn = _get_conn()
        cur = conn.cursor()
    try:
        if lock_timeout_ms is not None:
            cur.execute(
                "SELECT set_config('lock_timeout', %s, true)",
                (f"{int(lock_timeout_ms)}ms",),
            )
        if statement_timeout_ms is not None:
            cur.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (f"{int(statement_timeout_ms)}ms",),
            )
        yield conn, cur
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            _discard_cached_conn()
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dict(cur, row) -> dict[str, Any] | None:
    if not row:
        return None
    cols = [d.name for d in cur.description]
    data = dict(zip(cols, row, strict=False))
    meta = data.get("meta")
    if isinstance(meta, str):
        data["meta"] = json.loads(meta) if meta else {}
    return data


def fetch_run(run_id: str) -> dict[str, Any] | None:
    with db_cursor() as (_, cur):
        cur.execute("SELECT * FROM hotel_mapping_runs WHERE id = %s", (run_id,))
        return _row_to_dict(cur, cur.fetchone())


def fetch_region_run(run_id: str) -> dict[str, Any] | None:
    with db_cursor() as (_, cur):
        cur.execute("SELECT * FROM region_mapping_runs WHERE id = %s", (run_id,))
        return _row_to_dict(cur, cur.fetchone())


def is_cancelled(run: dict[str, Any] | None) -> bool:
    if not run:
        return True
    if run.get("status") == "cancelled":
        return True
    meta = run.get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    return bool(meta.get("cancelled"))


def load_region_map(booking_source_id: str) -> dict[str, str]:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT booking_source_region_code, new_cities_n_region_id
            FROM booking_source_region_map
            WHERE booking_source_id = %s
            """,
            (booking_source_id,),
        )
        return {str(code): str(region_id) for code, region_id in cur.fetchall()}


def update_run(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    sets = []
    values: list[Any] = []
    for key, value in fields.items():
        if key == "meta" and isinstance(value, dict):
            value = json.dumps(value)
        sets.append(f"{key} = %s")
        values.append(value)
    sets.append("updated_at = %s")
    values.append(_utc_now())
    values.append(run_id)
    with db_cursor() as (_, cur):
        cur.execute(
            f"UPDATE hotel_mapping_runs SET {', '.join(sets)} WHERE id = %s",
            tuple(values),
        )


def update_region_run(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    sets = []
    values: list[Any] = []
    for key, value in fields.items():
        if key == "meta" and isinstance(value, dict):
            value = json.dumps(value)
        sets.append(f"{key} = %s")
        values.append(value)
    sets.append("updated_at = %s")
    values.append(_utc_now())
    values.append(run_id)
    with db_cursor() as (_, cur):
        cur.execute(
            f"UPDATE region_mapping_runs SET {', '.join(sets)} WHERE id = %s",
            tuple(values),
        )


def merge_meta(run_id: str, table: str, patch: dict[str, Any]) -> dict[str, Any]:
    fetcher = fetch_region_run if table == "region_mapping_runs" else fetch_run
    updater = update_region_run if table == "region_mapping_runs" else update_run
    run = fetcher(run_id)
    meta = (run or {}).get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    meta.update(patch)
    updater(run_id, meta=meta)
    return meta


def create_region_run(booking_source_id: str, source: str = "admin") -> str:
    run_id = str(uuid4())
    now = _utc_now()
    meta = {"phase": "pending", "engine": "python", "booking_source_id": booking_source_id}
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO region_mapping_runs (
                id, booking_source_id, source, status,
                processed_count, matched_count, skipped_count, cities_count,
                meta, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, 0, 0, 0, 0, %s::jsonb, %s, %s)
            """,
            (run_id, booking_source_id, source, "pending", json.dumps(meta), now, now),
        )
    return run_id


def create_parent_run(booking_source_id: str, source: str = "admin") -> str:
    run_id = str(uuid4())
    now = _utc_now()
    meta = {
        "phase": "pending",
        "mode": "python_stream",
        "engine": "python",
        "booking_source_id": booking_source_id,
    }
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO hotel_mapping_runs (
                id, booking_source_id, dump_type, source, status, meta, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (run_id, booking_source_id, "full", source, "pending", json.dumps(meta), now, now),
        )
    return run_id


def create_wipe_run(booking_source_id: str, source: str = "admin") -> str:
    run_id = str(uuid4())
    now = _utc_now()
    meta = {
        "phase": "wiping",
        "mode": "wipe",
        "engine": "python",
        "wipe_phase": "queued",
        "booking_source_id": booking_source_id,
    }
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO hotel_mapping_runs (
                id, booking_source_id, dump_type, source, status, meta, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (run_id, booking_source_id, "wipe", source, "pending", json.dumps(meta), now, now),
        )
    return run_id


def has_active_wipe_run(booking_source_id: str) -> bool:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'wipe'
              AND status IN ('pending', 'running')
            """,
            (booking_source_id,),
        )
        return int(cur.fetchone()[0] or 0) > 0


def has_active_parent_run(booking_source_id: str) -> bool:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'full'
              AND status IN ('pending', 'running')
            """,
            (booking_source_id,),
        )
        return int(cur.fetchone()[0] or 0) > 0


def has_active_region_run(booking_source_id: str) -> bool:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COUNT(*) FROM region_mapping_runs
            WHERE booking_source_id = %s
              AND status IN ('pending', 'running')
            """,
            (booking_source_id,),
        )
        return int(cur.fetchone()[0] or 0) > 0


def find_resumable_full_stream_run(booking_source_id: str) -> str | None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT id, meta FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'full'
              AND status IN ('running', 'failed')
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (booking_source_id,),
        )
        for run_id, meta_raw in cur.fetchall():
            if isinstance(meta_raw, str):
                meta = json.loads(meta_raw) if meta_raw else {}
            elif isinstance(meta_raw, dict):
                meta = meta_raw
            else:
                meta = {}
            if meta.get("streaming_wiped"):
                continue
            streaming = meta.get("streaming") if isinstance(meta.get("streaming"), dict) else {}
            if streaming.get("zst_path") or meta.get("mode") == "python_stream":
                return str(run_id)
    return None


def cancel_active_region_runs(booking_source_id: str) -> int:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT id, meta FROM region_mapping_runs
            WHERE booking_source_id = %s AND status IN ('pending', 'running')
            """,
            (booking_source_id,),
        )
        rows = cur.fetchall()
        n = 0
        now = _utc_now()
        for run_id, meta_raw in rows:
            meta = meta_raw if isinstance(meta_raw, dict) else (json.loads(meta_raw) if meta_raw else {})
            meta["cancelled"] = True
            meta["phase"] = "cancelled"
            cur.execute(
                """
                UPDATE region_mapping_runs
                SET status = 'cancelled', finished_at = %s, meta = %s::jsonb, updated_at = %s
                WHERE id = %s
                """,
                (now, json.dumps(meta), now, run_id),
            )
            n += 1
        return n


def cancel_active_hotel_runs(booking_source_id: str) -> int:
    from . import process_kill

    to_kill: list[int] = []
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT id, meta FROM hotel_mapping_runs
            WHERE booking_source_id = %s AND status IN ('pending', 'running')
            """,
            (booking_source_id,),
        )
        rows = cur.fetchall()
        n = 0
        now = _utc_now()
        for run_id, meta_raw in rows:
            meta = meta_raw if isinstance(meta_raw, dict) else (json.loads(meta_raw) if meta_raw else {})
            to_kill.extend(process_kill.pids_from_meta(meta))
            meta["cancelled"] = True
            meta["phase"] = "cancelled"
            cur.execute(
                """
                UPDATE hotel_mapping_runs
                SET status = 'cancelled', finished_at = %s, meta = %s::jsonb, updated_at = %s
                WHERE id = %s
                """,
                (now, json.dumps(meta), now, run_id),
            )
            n += 1
    # Release DB locks held by stream/promote workers so wipe can proceed.
    process_kill.kill_pids(to_kill)
    return n


def cancel_region_run(run_id: str) -> None:
    run = fetch_region_run(run_id)
    meta = (run or {}).get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    meta["cancelled"] = True
    update_region_run(run_id, status="cancelled", finished_at=_utc_now(), meta=meta)


def cancel_hotel_run(run_id: str) -> None:
    run = fetch_run(run_id)
    meta = (run or {}).get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    meta["cancelled"] = True
    update_run(run_id, status="cancelled", finished_at=_utc_now(), meta=meta)


def count_region_mappings(booking_source_id: str) -> int:
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT COUNT(*) FROM booking_source_region_map WHERE booking_source_id = %s",
            (booking_source_id,),
        )
        return int(cur.fetchone()[0] or 0)


def clear_region_mappings(booking_source_id: str) -> int:
    with db_cursor() as (_, cur):
        cur.execute(
            "DELETE FROM booking_source_region_map WHERE booking_source_id = %s",
            (booking_source_id,),
        )
        return cur.rowcount or 0


def clear_staging_for_booking_source(booking_source_id: str) -> dict[str, int]:
    from . import crs_reset

    stats = crs_reset.clear_staging_batched(booking_source_id)
    return {
        "staging_hotels": int(stats.get("stagingHotelsDeleted") or 0),
        "staging_rooms": int(stats.get("stagingRoomsDeleted") or 0),
    }


def latest_hotel_run(booking_source_id: str) -> dict[str, Any] | None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT * FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'full'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (booking_source_id,),
        )
        return _row_to_dict(cur, cur.fetchone())


def latest_wipe_run(booking_source_id: str) -> dict[str, Any] | None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT * FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'wipe'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (booking_source_id,),
        )
        return _row_to_dict(cur, cur.fetchone())


def active_wipe_run(booking_source_id: str) -> dict[str, Any] | None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT * FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'wipe'
              AND status IN ('pending', 'running')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (booking_source_id,),
        )
        return _row_to_dict(cur, cur.fetchone())



def count_staging_hotels(run_id: str) -> int:
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT COUNT(*) FROM staging_hotels WHERE mapping_run_id = %s",
            (run_id,),
        )
        return int(cur.fetchone()[0] or 0)


def count_staging_rooms(run_id: str) -> int:
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT COUNT(*) FROM staging_rooms WHERE mapping_run_id = %s",
            (run_id,),
        )
        return int(cur.fetchone()[0] or 0)


def latest_region_run(booking_source_id: str) -> dict[str, Any] | None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT * FROM region_mapping_runs
            WHERE booking_source_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (booking_source_id,),
        )
        return _row_to_dict(cur, cur.fetchone())


def flush_staging(
    run_id: str,
    shard_index: int,
    hotel_batch: list[dict[str, Any]],
    room_batch: list[dict[str, Any]],
) -> None:
    if not hotel_batch and not room_batch:
        return
    now = _utc_now()
    hotel_rows = []
    for hotel in hotel_batch:
        hotel_rows.append(
            (
                str(uuid4()),
                run_id,
                shard_index,
                hotel["supplier_hotel_code"],
                hotel["dedupe_key"],
                hotel.get("region_id"),
                hotel.get("code"),
                hotel["name"],
                hotel.get("star_rating") or 0,
                hotel.get("description") or "",
                hotel.get("address_line1") or "",
                hotel.get("address_line2") or "",
                hotel.get("postal_code") or "",
                hotel.get("location") or "",
                hotel.get("latitude"),
                hotel.get("longitude"),
                hotel.get("phone") or "",
                hotel.get("email") or "",
                hotel.get("image") or "",
                json_dumps(hotel.get("amenity_names") or []),
                json_dumps(hotel.get("image_urls") or []),
                json_dumps(hotel.get("room_payload") or []),
                json_dumps(hotel.get("policy_payload") or {}),
                hotel.get("accommodation_type"),
                hotel.get("hotel_chain"),
                hotel.get("check_in_time"),
                hotel.get("check_in_time_end"),
                hotel.get("check_out_time"),
                hotel.get("front_desk_time_start"),
                hotel.get("front_desk_time_end"),
                json_dumps(hotel.get("content_payload") or {}),
                now,
                now,
            )
        )
    seen_rooms: set[str] = set()
    room_rows = []
    for room in room_batch:
        key = f"{room['supplier_hotel_code']}|{room['room_group_id']}"
        if key in seen_rooms:
            continue
        seen_rooms.add(key)
        room_rows.append(
            (
                str(uuid4()),
                run_id,
                shard_index,
                room["supplier_hotel_code"],
                room["room_group_id"],
                room.get("name") or "",
                room.get("main_name"),
                room.get("description") or "",
                json_dumps(room.get("amenity_slugs") or []),
                json_dumps(room.get("image_urls") or []),
                json_dumps(room.get("rg_ext") or {}),
                json_dumps(room.get("name_struct") or {}),
                json_dumps(room.get("images_ext") or []),
                now,
                now,
            )
        )

    with db_cursor() as (_, cur):
        if hotel_rows:
            cur.executemany(
                """
                INSERT INTO staging_hotels (
                    id, mapping_run_id, shard_index, supplier_hotel_code, dedupe_key, region_id,
                    code, name, star_rating, description,
                    address_line1, address_line2, postal_code, location,
                    latitude, longitude, phone, email, image,
                    amenity_names, image_urls, room_payload, policy_payload,
                    accommodation_type, hotel_chain,
                    check_in_time, check_in_time_end, check_out_time,
                    front_desk_time_start, front_desk_time_end, content_payload,
                    created_at, updated_at
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,
                    %s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s
                )
                """,
                hotel_rows,
            )
        if room_rows:
            cur.executemany(
                """
                INSERT INTO staging_rooms (
                    id, mapping_run_id, shard_index, supplier_hotel_code, room_group_id,
                    name, main_name, description, amenity_slugs, image_urls,
                    rg_ext, name_struct, images_ext, created_at, updated_at
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,
                    %s::jsonb,%s::jsonb,%s::jsonb,%s,%s
                )
                ON CONFLICT (mapping_run_id, supplier_hotel_code, room_group_id) DO NOTHING
                """,
                room_rows,
            )


def delete_staging_for_run(run_id: str, *, batch_size: int = 2000) -> dict[str, int]:
    """Delete staging hotels/rooms for one mapping run in committed batches."""
    rooms_deleted = 0
    hotels_deleted = 0
    while True:
        with db_cursor() as (_, cur):
            cur.execute(
                """
                SELECT id FROM staging_rooms
                WHERE mapping_run_id = %s
                ORDER BY id
                LIMIT %s
                """,
                (run_id, batch_size),
            )
            ids = [str(r[0]) for r in cur.fetchall()]
            if not ids:
                break
            ph = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM staging_rooms WHERE id IN ({ph})", tuple(ids))
            rooms_deleted += len(ids)
    while True:
        with db_cursor() as (_, cur):
            cur.execute(
                """
                SELECT id FROM staging_hotels
                WHERE mapping_run_id = %s
                ORDER BY id
                LIMIT %s
                """,
                (run_id, batch_size),
            )
            ids = [str(r[0]) for r in cur.fetchall()]
            if not ids:
                break
            ph = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM staging_hotels WHERE id IN ({ph})", tuple(ids))
            hotels_deleted += len(ids)
    return {"stagingRoomsDeleted": rooms_deleted, "stagingHotelsDeleted": hotels_deleted}
